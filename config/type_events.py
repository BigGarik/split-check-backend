class Events:
    BILL_DETAIL_EVENT = 'billDetailEvent'
    ALL_BILL_EVENT = 'allBillEvent'
    CHECK_ADD_EVENT = 'checkAddEvent'
    JOIN_BILL_EVENT_STATUS = 'joinBillEventStatus'
    CHECK_DELETE_EVENT_STATUS = 'checkDeleteEventStatus'

    IMAGE_RECOGNITION_EVENT = 'imageRecognitionEvent'
    IMAGE_RECOGNITION_EVENT_STATUS = 'imageRecognitionEventStatus'

    ITEM_ADD_EVENT = 'itemAddEvent'
    ITEM_ADD_EVENT_STATUS = 'itemAddEventStatus'
    ITEM_REMOVE_EVENT = 'itemRemoveEvent'
    ITEM_REMOVE_EVENT_STATUS = 'itemRemoveEventStatus'
    ITEM_EDIT_EVENT = 'itemEditEvent'
    ITEM_EDIT_EVENT_STATUS = 'itemEditEventStatus'
    ITEM_SPLIT_EVENT = 'itemSplitEvent'
    ITEM_SPLIT_EVENT_STATUS = 'itemSplitEventStatus'

    USER_PROFILE_DATA_RECEIVED_EVENT = 'userProfileDataReceivedEvent'
    USER_PROFILE_DATA_UPDATE_EVENT = 'userProfileDataUpdateEvent'

    CHECK_SELECTION_EVENT = 'checkSelectionEvent'
    CHECK_SELECTION_EVENT_STATUS = 'checkSelectionEventStatus'


EVENT_DESCRIPTIONS = {
    Events.BILL_DETAIL_EVENT: "Получение детальной информации по конкретному счету",
    Events.ALL_BILL_EVENT: "Получение списка всех доступных счетов",
    Events.CHECK_ADD_EVENT: "Добавление нового чека к счету",
    Events.JOIN_BILL_EVENT_STATUS: "Статус присоединения пользователя к счету",
    Events.CHECK_DELETE_EVENT_STATUS: "Статус удаления чека из счета",

    Events.IMAGE_RECOGNITION_EVENT: "Начало процесса распознавания изображения",
    Events.IMAGE_RECOGNITION_EVENT_STATUS: "Статус процесса распознавания изображения",

    Events.ITEM_ADD_EVENT: "Добавление нового элемента (товара) в счет",
    Events.ITEM_ADD_EVENT_STATUS: "Статус добавления нового элемента в счет",
    Events.ITEM_REMOVE_EVENT: "Удаление элемента из счета",
    Events.ITEM_REMOVE_EVENT_STATUS: "Статус удаления элемента из счета",
    Events.ITEM_EDIT_EVENT: "Изменение данных элемента в счете",
    Events.ITEM_EDIT_EVENT_STATUS: "Статус изменения элемента в счете",
    Events.ITEM_SPLIT_EVENT: "Разделение элемента между пользователями",
    Events.ITEM_SPLIT_EVENT_STATUS: "Статус разделения элемента между пользователями",

    Events.USER_PROFILE_DATA_RECEIVED_EVENT: "Получение данных профиля пользователя",
    Events.USER_PROFILE_DATA_UPDATE_EVENT: "Обновление данных профиля пользователя",

    Events.CHECK_SELECTION_EVENT: "Пользователь выбирает чек",
    Events.CHECK_SELECTION_EVENT_STATUS: "Статус выбора чека пользователем",
}
