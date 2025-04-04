import asyncio
import os
import warnings
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import List, Dict, Any

import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

warnings.filterwarnings('ignore')


class AsyncImageClassifier:
    def __init__(
            self,
            model_name: str = "openai/clip-vit-base-patch32",
            batch_size: int = 4,
            num_threads: int = None
    ):
        self.num_threads = num_threads or min(os.cpu_count(), 4)
        self.batch_size = batch_size
        self.executor = ThreadPoolExecutor(max_workers=self.num_threads)

        torch.set_num_threads(self.num_threads)
        torch.set_num_interop_threads(max(1, self.num_threads // 2))
        torch.backends.cpu.enabled = True

        if hasattr(torch.backends, 'mkl'):
            torch.backends.mkl.enabled = True

        self._initialize_model(model_name)
        self._setup_categories()
        self.text_inputs_prepared = self._prepare_text_inputs()

    def _initialize_model(self, model_name: str) -> None:
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)

        self.model.eval()
        for param in self.model.parameters():
            param.requires_grad = False

        if torch.backends.mkl.is_available():
            torch.backends.mkl.enabled = True

    def _setup_categories(self) -> None:
        self.categories = {
            'receipt': ['a receipt or invoice', 'a document or paper', 'a ticket or bill'],
            'unsafe': ['porn or explicit content', 'nudity or naked body'],
            'unwanted': ['a person or human', 'an animal or pet', 'a child or baby',
                         'a blank photo or dark photo', 'a clothes or accessory']
        }
        self.text_inputs = sum(self.categories.values(), [])
        self.category_map = {
            'receipt': "Allowed Content",
            'unsafe': "Inappropriate Content",
            'unwanted': "Unwanted Content"
        }

    @lru_cache(maxsize=1)
    def _prepare_text_inputs(self) -> Dict[str, torch.Tensor]:
        return self.processor(text=self.text_inputs, return_tensors="pt", padding=True)

    async def _load_image(self, image_path: str) -> Image.Image:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self.executor, Image.open, image_path)
        except Exception as e:
            raise RuntimeError(f"Ошибка при загрузке изображения {image_path}: {str(e)}")

    async def _process_image(self, image: Image.Image) -> Dict[str, torch.Tensor]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            lambda: self.processor(images=image, return_tensors="pt", padding=True)
        )

    async def _load_and_process_image(self, image_path: str) -> Dict[str, torch.Tensor]:
        image = await self._load_image(image_path)
        return await self._process_image(image)

    def _get_category_type(self, category: str) -> str:
        for cat_type, cat_list in self.categories.items():
            if category in cat_list:
                return self.category_map.get(cat_type, "Unknown Content")
        return "Unknown Content"

    @torch.inference_mode()
    def _batch_predict(self, batch_inputs: Dict[str, torch.Tensor]) -> List[Dict[str, Any]]:
        inputs = {**batch_inputs, **self.text_inputs_prepared}
        outputs = self.model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)
        max_probs, max_indices = torch.max(probs, dim=1)

        results = []
        for prob, idx in zip(max_probs, max_indices):
            category = self.text_inputs[idx.item()]
            confidence = prob.item() * 100
            results.append({
                "category": category,
                "confidence": f"{confidence:.2f}%",
                "content_type": self._get_category_type(category)
            })

        if hasattr(torch.cuda, 'empty_cache'):
            torch.cuda.empty_cache()

        return results

    async def classify_images(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        results = []
        for i in range(0, len(image_paths), self.batch_size):
            batch_paths = image_paths[i:i + self.batch_size]
            batch_inputs_list = await asyncio.gather(
                *[self._load_and_process_image(path) for path in batch_paths]
            )
            batch_inputs = {
                k: torch.cat([inputs[k] for inputs in batch_inputs_list])
                for k in batch_inputs_list[0].keys()
            }
            batch_results = self._batch_predict(batch_inputs)
            results.extend(batch_results)
            del batch_inputs_list, batch_inputs  # Очистка
        return results

    async def classify_image(self, image_path: str) -> Dict[str, Any]:
        results = await self.classify_images([image_path])
        return results[0]

    def cleanup(self):
        if self.executor:
            self.executor.shutdown()
        if hasattr(self.model, 'cpu'):
            self.model.cpu()  # Переместить модель на CPU
        del self.model  # Удалить ссылку на модель
        del self.processor
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
