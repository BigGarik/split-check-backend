import logging
import base64
from io import BytesIO

from PIL import Image
import os

logger = logging.getLogger(__name__)


def convert_to_png(img):
    # Конвертируем изображение в PNG
    with BytesIO() as buffer:
        img.save(buffer, format="PNG")
        return buffer.getvalue()


def convert_img(input_path, output_path=None, short_side=None):
    try:
        # Открываем изображение
        with Image.open(input_path) as img:
            # Если выходной путь не указан, создаем его на основе входного
            if output_path is None:
                file_name = os.path.splitext(os.path.basename(input_path))[0]
                output_path = os.path.join(os.path.dirname(input_path), f"{file_name}.png")

            # Изменяем размер изображения, если указана короткая сторона
            if short_side:
                # Определяем текущие размеры
                width, height = img.size

                # Определяем, какая сторона короче
                if width < height:
                    new_width = short_side
                    new_height = int(height * (short_side / width))
                else:
                    new_height = short_side
                    new_width = int(width * (short_side / height))

                # Изменяем размер изображения с сохранением пропорций
                img = img.resize((new_width, new_height), Image.LANCZOS)

            # Конвертируем и сохраняем изображение в формате PNG
            img.save(output_path, "PNG", quality=95)

        print(f"Изображение успешно сконвертировано и сохранено: {output_path}")
        return output_path
    except Exception as e:
        print(f"Произошла ошибка при конвертации изображения: {str(e)}")
        return False


def get_base64_encoded_image(image_path):
    with open(image_path, "rb") as image_file:
        binary_data = image_file.read()
        base_64_encoded_data = base64.b64encode(binary_data)
        base64_string = base_64_encoded_data.decode('utf-8')
        return base64_string


if __name__ == '__main__':
    # convert_img("../images/IMG_0833.JPEG", short_side=1024)
    pass
