/* =========================================================
   STOREFLOW MULTI-WAREHOUSE WMS
========================================================= */


/* =========================================================
   STORAGE
========================================================= */

const STORAGE = {
    users: "storeflow_users",
    session: "storeflow_session",
    tempSession: "storeflow_temp_session",

    warehouses: "storeflow_warehouses",
    products: "storeflow_products",
    counterparties: "storeflow_counterparties",
    imports: "storeflow_imports",
    sales: "storeflow_sales",

    settings: "storeflow_settings",

    language: "storeflow_language",
    theme: "storeflow_theme"
};


/* =========================================================
   TRANSLATIONS
========================================================= */

const I18N = {

    uz: {

        workspace: "Ish maydoni",
        systemActive: "Tizim faol",

        operations: "Operatsiyalar",
        analytics: "Analitika va boshqaruv",

        dashboard: "Boshqaruv paneli",
        warehouses: "Omborlar",
        stockBalances: "Qoldiqlar",
        imports: "Kirim",
        sales: "Sotuvlar",
        products: "Mahsulotlar",
        counterparties: "Kontragentlar",
        reports: "Hisobotlar",
        users: "Foydalanuvchilar",
        settings: "Sozlamalar",

        logout: "Chiqish",

        globalSearch:
            "Mahsulot yoki hujjatni qidirish...",

        welcome: "Xush kelibsiz",

        heroDescription:
            "Barcha omborlar, kirim va sotuvlarni yagona tizimda boshqaring.",

        activeWarehouses:
            "Faol omborlar",

        stockUnits:
            "Ombordagi mahsulotlar",

        stockPurchaseValue:
            "Qoldiq tannarxi",

        todayRevenue:
            "Bugungi tushum",

        units:
            "dona",

        salesDynamics:
            "Sotuvlar dinamikasi",

        lastSevenDays:
            "Oxirgi 7 kun",

        warehouseDistribution:
            "Omborlar bo‘yicha qoldiq",

        warehouseDistributionDescription:
            "Mahsulot miqdori taqsimoti",

        recentOperations:
            "So‘nggi operatsiyalar",

        latestStockMovements:
            "So‘nggi kirim va sotuvlar",

        lowStock:
            "Kam qoldiq",

        requiresAttention:
            "Omborlar kesimida",

        document: "Hujjat",
        operation: "Operatsiya",
        warehouse: "Ombor",
        amount: "Summa",
        date: "Sana",

        warehouseSearchPlaceholder:
            "Ombor nomi, kodi yoki manzili...",

        allWarehouseTypes:
            "Barcha turlar",

        warehouseUniversal:
            "Universal",

        warehouseElectronics:
            "Texnika",

        warehouseFood:
            "Oziq-ovqat",

        warehouseClothing:
            "Kiyim-kechak",

        warehouseHousehold:
            "Uy-ro‘zg‘or",

        warehouseOther:
            "Boshqa",

        addWarehouse:
            "Ombor qo‘shish",

        manager:
            "Mas’ul",

        address:
            "Manzil",

        capacity:
            "Sig‘im",

        positions:
            "Pozitsiyalar",

        quantity:
            "Miqdor",

        purchaseValue:
            "Tannarx qiymati",

        status:
            "Holat",

        warehouseModalDescription:
            "Yangi ombor uchun to‘liq ma’lumotlarni kiriting.",

        warehouseName:
            "Ombor nomi",

        warehouseCode:
            "Ombor kodi",

        warehouseType:
            "Ombor turi",

        area:
            "Maydon",

        temperature:
            "Harorat rejimi",

        notes:
            "Izoh",

        unitsShort:
            "dona",

        createWarehouse:
            "Ombor yaratish",

        stockSearch:
            "Mahsulot yoki artikul...",

        allWarehouses:
            "Barcha omborlar",

        allCategories:
            "Barcha kategoriyalar",

        allStock:
            "Barcha qoldiqlar",

        available:
            "Mavjud",

        outOfStock:
            "Qolmagan",

        printStock:
            "Qoldiqni chop etish",

        retailValue:
            "Sotuv qiymati",

        product:
            "Mahsulot",

        sku:
            "Artikul",

        category:
            "Kategoriya",

        purchasePrice:
            "Xarid narxi",

        salePrice:
            "Sotuv narxi",

        stock:
            "Qoldiq",

        stockAmount:
            "Qoldiq summasi",

        importsSearch:
            "Hujjat, kontragent yoki mahsulot...",

        importReport:
            "Kirim hisoboti",

        periodReportDescription:
            "Kun yoki davr bo‘yicha hisobot",

        today:
            "Bugun",

        daysShort:
            "kun",

        thisMonth:
            "Bu oy",

        allPeriod:
            "Barchasi",

        apply:
            "Qo‘llash",

        printReport:
            "Hisobotni chop etish",

        documents:
            "Hujjatlar",

        receivedUnits:
            "Qabul qilingan",

        purchaseTotal:
            "Xarid summasi",

        potentialRetail:
            "Potensial sotuv",

        responsible:
            "Mas’ul",

        newImport:
            "Yangi kirim",

        salesSearch:
            "Sotuv, mahsulot yoki xaridor...",

        salesReport:
            "Sotuv hisoboti",

        salesCount:
            "Sotuvlar",

        soldUnits:
            "Sotilgan",

        revenue:
            "Tushum",

        profit:
            "Foyda",

        newSale:
            "Yangi sotuv",

        productsSearch:
            "Mahsulot, artikul yoki brend...",

        brand:
            "Brend",

        markup:
            "Ustama",

        addProduct:
            "Mahsulot qo‘shish",

        counterpartiesSearch:
            "Nomi, STIR yoki telefon...",

        allTypes:
            "Barcha turlar",

        supplier:
            "Yetkazib beruvchi",

        buyer:
            "Xaridor",

        both:
            "Ikkalasi",

        addCounterparty:
            "Kontragent qo‘shish",

        suppliers:
            "Yetkazib beruvchilar",

        buyers:
            "Xaridorlar",

        counterparty:
            "Kontragent",

        type:
            "Turi",

        inn:
            "STIR",

        phone:
            "Telefon",

        contactPerson:
            "Aloqa shaxsi",

        financialReports:
            "Moliyaviy va ombor hisoboti",

        financialReportsDescription:
            "Hisobotlarni barcha yoki alohida ombor kesimida tahlil qiling.",

        printFullReport:
            "To‘liq hisobotni chop etish",

        dateFrom:
            "Sanadan",

        dateTo:
            "Sanagacha",

        costOfSales:
            "Sotilgan mahsulot tannarxi",

        salesByCategory:
            "Kategoriya bo‘yicha sotuvlar",

        revenueStructure:
            "Tushum tuzilmasi",

        warehouseSummary:
            "Ombor xulosasi",

        potentialProfit:
            "Potensial foyda",

        user:
            "Foydalanuvchi",

        login:
            "Login",

        role:
            "Rol",

        lastLogin:
            "So‘nggi kirish",

        created:
            "Yaratilgan",

        usersSearch:
            "F.I.Sh, login yoki rol...",

        addUser:
            "Foydalanuvchi qo‘shish",

        systemSettings:
            "Tizim sozlamalari",

        settingsDescription:
            "Do‘kon, hujjatlar va ombor parametrlarini boshqaring.",

        companyName:
            "Do‘kon nomi",

        currency:
            "Valyuta",

        importPrefix:
            "Kirim prefiksi",

        salePrefix:
            "Sotuv prefiksi",

        minimumStock:
            "Minimal qoldiq",

        saveChanges:
            "O‘zgarishlarni saqlash",

        productModalDescription:
            "Mahsulot kartochkasi va boshlang‘ich omborini yarating.",

        productPhoto:
            "Mahsulot rasmi",

        photoDescription:
            "JPG, PNG yoki WEBP",

        noPhoto:
            "Rasm yo‘q",

        selectPhoto:
            "Rasm tanlash",

        subcategory:
            "Quyi kategoriya",

        productName:
            "Mahsulot nomi",

        model:
            "Model",

        barcode:
            "Shtrix-kod",

        unit:
            "O‘lchov birligi",

        openingStock:
            "Boshlang‘ich qoldiq",

        location:
            "Tokcha / joylashuv",

        cancel:
            "Bekor qilish",

        createProduct:
            "Mahsulot yaratish",

        supplierInvoice:
            "Yetkazib beruvchi hujjati",

        retailTotal:
            "Sotuv summasi",

        postImport:
            "Kirim qilish",

        discount:
            "Chegirma",

        subtotal:
            "Oraliq summa",

        totalPayable:
            "To‘lov summasi",

        completeSale:
            "Sotuvni amalga oshirish",

        counterpartyModalDescription:
            "Yetkazib beruvchi yoki xaridor yarating.",

        bankDetails:
            "Bank rekvizitlari",

        saveCounterparty:
            "Kontragentni saqlash",

        fullName:
            "F.I.Sh.",

        password:
            "Parol",

        confirmPassword:
            "Parolni takrorlang",

        createUser:
            "Foydalanuvchi yaratish",

        delete:
            "O‘chirish",

        active:
            "Faol",

        inactive:
            "Faol emas",

        importOperation:
            "Kirim",

        saleOperation:
            "Sotuv",

        retailCustomer:
            "Chakana xaridor",

        noData:
            "Ma’lumot topilmadi",

        noLowStock:
            "Kam qoldiqli mahsulot yo‘q",

        warehouseCreated:
            "Ombor yaratildi",

        productCreated:
            "Mahsulot yaratildi",

        importCreated:
            "Kirim amalga oshirildi",

        saleCreated:
            "Sotuv amalga oshirildi",

        counterpartyCreated:
            "Kontragent yaratildi",

        userCreated:
            "Foydalanuvchi yaratildi",

        settingsSaved:
            "Sozlamalar saqlandi",

        error:
            "Xatolik",

        warehouseHasStock:
            "Bu omborda mahsulot qoldig‘i mavjud. Avval qoldiqni boshqa omborga ko‘chiring yoki nolga tushiring.",

        warehouseHasDocuments:
            "Ushbu ombor bo‘yicha kirim yoki sotuv hujjatlari mavjud. Uni o‘chirib bo‘lmaydi.",

        insufficientStock:
            "Tanlangan omborda yetarli mahsulot yo‘q.",

        passwordsMismatch:
            "Parollar bir xil emas.",

        loginExists:
            "Bunday login mavjud.",

        warehouseCodeExists:
            "Bunday ombor kodi mavjud.",

        deleteWarehouse:
            "Omborni o‘chirish?",

        deleteProduct:
            "Mahsulotni o‘chirish?",

        deleteCounterparty:
            "Kontragentni o‘chirish?",

        deleteUser:
            "Foydalanuvchini o‘chirish?",

        reportTitle:
            "To‘liq ombor va savdo hisoboti",

        importReportTitle:
            "Kirim bo‘yicha hisobot",

        salesReportTitle:
            "Sotuvlar bo‘yicha hisobot",

        stockReportTitle:
            "Ombor qoldig‘i hisoboti",

        reportingPeriod:
            "Hisobot davri",

        reportWarehouse:
            "Hisobot ombori",

        reportCreated:
            "Hisobot tuzilgan",

        importList:
            "Kirimlar ro‘yxati",

        salesList:
            "Sotuvlar ro‘yxati",

        stockList:
            "Ombor qoldiqlari",

        cost:
            "Tannarx",

        periodAll:
            "Barcha davr",

        dashboardSubtitle:
            "Barcha omborlarning asosiy ko‘rsatkichlari",

        warehousesSubtitle:
            "Omborlar, sig‘im va qoldiqlar boshqaruvi",

        stockSubtitle:
            "Mahsulot qoldiqlari omborlar kesimida",

        importsSubtitle:
            "Kirimlar va qabul qiluvchi omborlar",

        salesSubtitle:
            "Sotuv va ombordan chiqim",

        productsSubtitle:
            "Mahsulot kartochkalari va omborlar bo‘yicha qoldiq",

        counterpartiesSubtitle:
            "Yetkazib beruvchilar va xaridorlar",

        reportsSubtitle:
            "Moliyaviy va ombor analitikasi",

        usersSubtitle:
            "Hisoblar, rollar va kirish huquqlari",

        settingsSubtitle:
            "Tizim va hujjatlar parametrlari"
    },


    ru: {

        workspace: "Рабочая область",
        systemActive: "Система активна",

        operations: "Операции",
        analytics: "Аналитика и управление",

        dashboard: "Обзор",
        warehouses: "Склады",
        stockBalances: "Остатки",
        imports: "Приход",
        sales: "Продажи",
        products: "Товары",
        counterparties: "Контрагенты",
        reports: "Отчеты",
        users: "Пользователи",
        settings: "Настройки",

        logout: "Выйти",

        globalSearch:
            "Поиск товара или документа...",

        welcome: "Добро пожаловать",

        heroDescription:
            "Управляйте всеми складами, приходами и продажами в единой системе.",

        activeWarehouses:
            "Активных складов",

        stockUnits:
            "Товаров на складах",

        stockPurchaseValue:
            "Стоимость остатков",

        todayRevenue:
            "Выручка сегодня",

        units:
            "единиц",

        salesDynamics:
            "Динамика продаж",

        lastSevenDays:
            "Последние 7 дней",

        warehouseDistribution:
            "Остатки по складам",

        warehouseDistributionDescription:
            "Распределение количества товаров",

        recentOperations:
            "Последние операции",

        latestStockMovements:
            "Последние приходы и продажи",

        lowStock:
            "Низкий остаток",

        requiresAttention:
            "По складам",

        document: "Документ",
        operation: "Операция",
        warehouse: "Склад",
        amount: "Сумма",
        date: "Дата",

        warehouseSearchPlaceholder:
            "Название, код или адрес склада...",

        allWarehouseTypes:
            "Все типы",

        warehouseUniversal:
            "Универсальный",

        warehouseElectronics:
            "Техника",

        warehouseFood:
            "Продукты",

        warehouseClothing:
            "Одежда",

        warehouseHousehold:
            "Хозяйственные товары",

        warehouseOther:
            "Другой",

        addWarehouse:
            "Добавить склад",

        manager:
            "Ответственный",

        address:
            "Адрес",

        capacity:
            "Вместимость",

        positions:
            "Позиций",

        quantity:
            "Количество",

        purchaseValue:
            "Стоимость по закупке",

        status:
            "Статус",

        warehouseModalDescription:
            "Введите полную информацию о новом складе.",

        warehouseName:
            "Название склада",

        warehouseCode:
            "Код склада",

        warehouseType:
            "Тип склада",

        area:
            "Площадь",

        temperature:
            "Температурный режим",

        notes:
            "Примечание",

        unitsShort:
            "ед.",

        createWarehouse:
            "Создать склад",

        stockSearch:
            "Товар или артикул...",

        allWarehouses:
            "Все склады",

        allCategories:
            "Все категории",

        allStock:
            "Все остатки",

        available:
            "В наличии",

        outOfStock:
            "Нет в наличии",

        printStock:
            "Печать остатков",

        retailValue:
            "Стоимость продажи",

        product:
            "Товар",

        sku:
            "Артикул",

        category:
            "Категория",

        purchasePrice:
            "Цена закупки",

        salePrice:
            "Цена продажи",

        stock:
            "Остаток",

        stockAmount:
            "Сумма остатка",

        importsSearch:
            "Документ, контрагент или товар...",

        importReport:
            "Отчет по приходу",

        periodReportDescription:
            "Отчет за день или период",

        today:
            "Сегодня",

        daysShort:
            "дн.",

        thisMonth:
            "Этот месяц",

        allPeriod:
            "Весь период",

        apply:
            "Применить",

        printReport:
            "Печать отчета",

        documents:
            "Документов",

        receivedUnits:
            "Принято",

        purchaseTotal:
            "Сумма закупки",

        potentialRetail:
            "Потенциальная продажа",

        responsible:
            "Ответственный",

        newImport:
            "Новый приход",

        salesSearch:
            "Продажа, товар или покупатель...",

        salesReport:
            "Отчет по продажам",

        salesCount:
            "Продаж",

        soldUnits:
            "Продано",

        revenue:
            "Выручка",

        profit:
            "Прибыль",

        newSale:
            "Новая продажа",

        productsSearch:
            "Товар, артикул или бренд...",

        brand:
            "Бренд",

        markup:
            "Наценка",

        addProduct:
            "Добавить товар",

        counterpartiesSearch:
            "Название, ИНН или телефон...",

        allTypes:
            "Все типы",

        supplier:
            "Поставщик",

        buyer:
            "Покупатель",

        both:
            "Поставщик / покупатель",

        addCounterparty:
            "Добавить контрагента",

        suppliers:
            "Поставщиков",

        buyers:
            "Покупателей",

        counterparty:
            "Контрагент",

        type:
            "Тип",

        inn:
            "ИНН",

        phone:
            "Телефон",

        contactPerson:
            "Контактное лицо",

        financialReports:
            "Финансовая и складская отчетность",

        financialReportsDescription:
            "Анализируйте показатели по всем или отдельным складам.",

        printFullReport:
            "Печать полного отчета",

        dateFrom:
            "С даты",

        dateTo:
            "По дату",

        costOfSales:
            "Себестоимость продаж",

        salesByCategory:
            "Продажи по категориям",

        revenueStructure:
            "Структура выручки",

        warehouseSummary:
            "Сводка склада",

        potentialProfit:
            "Потенциальная прибыль",

        user:
            "Пользователь",

        login:
            "Логин",

        role:
            "Роль",

        lastLogin:
            "Последний вход",

        created:
            "Создан",

        usersSearch:
            "Ф.И.О., логин или роль...",

        addUser:
            "Добавить пользователя",

        systemSettings:
            "Настройки системы",

        settingsDescription:
            "Управляйте магазином, документами и складскими параметрами.",

        companyName:
            "Название магазина",

        currency:
            "Валюта",

        importPrefix:
            "Префикс прихода",

        salePrefix:
            "Префикс продажи",

        minimumStock:
            "Минимальный остаток",

        saveChanges:
            "Сохранить изменения",

        productModalDescription:
            "Создайте карточку товара и укажите начальный склад.",

        productPhoto:
            "Фото товара",

        photoDescription:
            "JPG, PNG или WEBP",

        noPhoto:
            "Нет фото",

        selectPhoto:
            "Выбрать фото",

        subcategory:
            "Подкатегория",

        productName:
            "Наименование товара",

        model:
            "Модель",

        barcode:
            "Штрихкод",

        unit:
            "Единица измерения",

        openingStock:
            "Начальный остаток",

        location:
            "Стеллаж / ячейка",

        cancel:
            "Отмена",

        createProduct:
            "Создать товар",

        supplierInvoice:
            "Накладная поставщика",

        retailTotal:
            "Сумма продажи",

        postImport:
            "Оприходовать",

        discount:
            "Скидка",

        subtotal:
            "Промежуточная сумма",

        totalPayable:
            "К оплате",

        completeSale:
            "Провести продажу",

        counterpartyModalDescription:
            "Создайте поставщика или покупателя.",

        bankDetails:
            "Банковские реквизиты",

        saveCounterparty:
            "Сохранить контрагента",

        fullName:
            "Ф.И.О.",

        password:
            "Пароль",

        confirmPassword:
            "Повторите пароль",

        createUser:
            "Создать пользователя",

        delete:
            "Удалить",

        active:
            "Активен",

        inactive:
            "Неактивен",

        importOperation:
            "Приход",

        saleOperation:
            "Продажа",

        retailCustomer:
            "Розничный покупатель",

        noData:
            "Данные не найдены",

        noLowStock:
            "Товаров с низким остатком нет",

        warehouseCreated:
            "Склад создан",

        productCreated:
            "Товар создан",

        importCreated:
            "Приход проведен",

        saleCreated:
            "Продажа проведена",

        counterpartyCreated:
            "Контрагент создан",

        userCreated:
            "Пользователь создан",

        settingsSaved:
            "Настройки сохранены",

        error:
            "Ошибка",

        warehouseHasStock:
            "На этом складе есть остатки. Сначала переместите товар или обнулите остатки.",

        warehouseHasDocuments:
            "По этому складу уже существуют документы прихода или продажи. Удаление запрещено.",

        insufficientStock:
            "На выбранном складе недостаточно товара.",

        passwordsMismatch:
            "Пароли не совпадают.",

        loginExists:
            "Такой логин уже существует.",

        warehouseCodeExists:
            "Такой код склада уже существует.",

        deleteWarehouse:
            "Удалить склад?",

        deleteProduct:
            "Удалить товар?",

        deleteCounterparty:
            "Удалить контрагента?",

        deleteUser:
            "Удалить пользователя?",

        reportTitle:
            "Полный отчет по складам и продажам",

        importReportTitle:
            "Отчет по приходам",

        salesReportTitle:
            "Отчет по продажам",

        stockReportTitle:
            "Отчет по остаткам",

        reportingPeriod:
            "Период отчета",

        reportWarehouse:
            "Склад отчета",

        reportCreated:
            "Отчет сформирован",

        importList:
            "Список приходов",

        salesList:
            "Список продаж",

        stockList:
            "Остатки",

        cost:
            "Себестоимость",

        periodAll:
            "Весь период",

        dashboardSubtitle:
            "Основные показатели всех складов",

        warehousesSubtitle:
            "Управление складами, вместимостью и остатками",

        stockSubtitle:
            "Остатки товаров в разрезе складов",

        importsSubtitle:
            "Приходы и склады-получатели",

        salesSubtitle:
            "Продажи и списание с выбранного склада",

        productsSubtitle:
            "Карточки товаров и остатки по складам",

        counterpartiesSubtitle:
            "Поставщики и покупатели",

        reportsSubtitle:
            "Финансовая и складская аналитика",

        usersSubtitle:
            "Учетные записи, роли и доступ",

        settingsSubtitle:
            "Параметры системы и документов"
    },


    en: {

        workspace: "Workspace",
        systemActive: "System active",

        operations: "Operations",
        analytics: "Analytics & management",

        dashboard: "Dashboard",
        warehouses: "Warehouses",
        stockBalances: "Stock",
        imports: "Purchases",
        sales: "Sales",
        products: "Products",
        counterparties: "Counterparties",
        reports: "Reports",
        users: "Users",
        settings: "Settings",

        logout: "Log out",

        globalSearch:
            "Search product or document...",

        welcome: "Welcome",

        heroDescription:
            "Manage all warehouses, purchases and sales from one system.",

        activeWarehouses:
            "Active warehouses",

        stockUnits:
            "Stock units",

        stockPurchaseValue:
            "Stock cost",

        todayRevenue:
            "Today's revenue",

        units:
            "units",

        salesDynamics:
            "Sales dynamics",

        lastSevenDays:
            "Last 7 days",

        warehouseDistribution:
            "Stock by warehouse",

        warehouseDistributionDescription:
            "Unit distribution",

        recentOperations:
            "Recent operations",

        latestStockMovements:
            "Latest purchases and sales",

        lowStock:
            "Low stock",

        requiresAttention:
            "By warehouse",

        document: "Document",
        operation: "Operation",
        warehouse: "Warehouse",
        amount: "Amount",
        date: "Date",

        warehouseSearchPlaceholder:
            "Warehouse name, code or address...",

        allWarehouseTypes:
            "All types",

        warehouseUniversal:
            "Universal",

        warehouseElectronics:
            "Electronics",

        warehouseFood:
            "Food",

        warehouseClothing:
            "Clothing",

        warehouseHousehold:
            "Household",

        warehouseOther:
            "Other",

        addWarehouse:
            "Add warehouse",

        manager:
            "Manager",

        address:
            "Address",

        capacity:
            "Capacity",

        positions:
            "Positions",

        quantity:
            "Quantity",

        purchaseValue:
            "Purchase value",

        status:
            "Status",

        warehouseModalDescription:
            "Enter full information for the new warehouse.",

        warehouseName:
            "Warehouse name",

        warehouseCode:
            "Warehouse code",

        warehouseType:
            "Warehouse type",

        area:
            "Area",

        temperature:
            "Temperature mode",

        notes:
            "Notes",

        unitsShort:
            "units",

        createWarehouse:
            "Create warehouse",

        stockSearch:
            "Product or SKU...",

        allWarehouses:
            "All warehouses",

        allCategories:
            "All categories",

        allStock:
            "All stock",

        available:
            "Available",

        outOfStock:
            "Out of stock",

        printStock:
            "Print stock",

        retailValue:
            "Retail value",

        product:
            "Product",

        sku:
            "SKU",

        category:
            "Category",

        purchasePrice:
            "Purchase price",

        salePrice:
            "Sale price",

        stock:
            "Stock",

        stockAmount:
            "Stock amount",

        importsSearch:
            "Document, counterparty or product...",

        importReport:
            "Purchase report",

        periodReportDescription:
            "Report by day or period",

        today:
            "Today",

        daysShort:
            "days",

        thisMonth:
            "This month",

        allPeriod:
            "All time",

        apply:
            "Apply",

        printReport:
            "Print report",

        documents:
            "Documents",

        receivedUnits:
            "Received",

        purchaseTotal:
            "Purchase total",

        potentialRetail:
            "Potential retail",

        responsible:
            "Responsible",

        newImport:
            "New purchase",

        salesSearch:
            "Sale, product or buyer...",

        salesReport:
            "Sales report",

        salesCount:
            "Sales",

        soldUnits:
            "Sold",

        revenue:
            "Revenue",

        profit:
            "Profit",

        newSale:
            "New sale",

        productsSearch:
            "Product, SKU or brand...",

        brand:
            "Brand",

        markup:
            "Markup",

        addProduct:
            "Add product",

        counterpartiesSearch:
            "Name, TIN or phone...",

        allTypes:
            "All types",

        supplier:
            "Supplier",

        buyer:
            "Buyer",

        both:
            "Supplier / buyer",

        addCounterparty:
            "Add counterparty",

        suppliers:
            "Suppliers",

        buyers:
            "Buyers",

        counterparty:
            "Counterparty",

        type:
            "Type",

        inn:
            "TIN",

        phone:
            "Phone",

        contactPerson:
            "Contact person",

        financialReports:
            "Financial and warehouse reporting",

        financialReportsDescription:
            "Analyze all warehouses or one selected warehouse.",

        printFullReport:
            "Print full report",

        dateFrom:
            "From",

        dateTo:
            "To",

        costOfSales:
            "Cost of sales",

        salesByCategory:
            "Sales by category",

        revenueStructure:
            "Revenue structure",

        warehouseSummary:
            "Warehouse summary",

        potentialProfit:
            "Potential profit",

        user:
            "User",

        login:
            "Login",

        role:
            "Role",

        lastLogin:
            "Last login",

        created:
            "Created",

        usersSearch:
            "Name, login or role...",

        addUser:
            "Add user",

        systemSettings:
            "System settings",

        settingsDescription:
            "Manage company, document and warehouse settings.",

        companyName:
            "Company name",

        currency:
            "Currency",

        importPrefix:
            "Purchase prefix",

        salePrefix:
            "Sale prefix",

        minimumStock:
            "Minimum stock",

        saveChanges:
            "Save changes",

        productModalDescription:
            "Create a product card and opening warehouse.",

        productPhoto:
            "Product photo",

        photoDescription:
            "JPG, PNG or WEBP",

        noPhoto:
            "No photo",

        selectPhoto:
            "Select photo",

        subcategory:
            "Subcategory",

        productName:
            "Product name",

        model:
            "Model",

        barcode:
            "Barcode",

        unit:
            "Unit",

        openingStock:
            "Opening stock",

        location:
            "Shelf / location",

        cancel:
            "Cancel",

        createProduct:
            "Create product",

        supplierInvoice:
            "Supplier invoice",

        retailTotal:
            "Retail total",

        postImport:
            "Post purchase",

        discount:
            "Discount",

        subtotal:
            "Subtotal",

        totalPayable:
            "Total payable",

        completeSale:
            "Complete sale",

        counterpartyModalDescription:
            "Create a supplier or buyer.",

        bankDetails:
            "Bank details",

        saveCounterparty:
            "Save counterparty",

        fullName:
            "Full name",

        password:
            "Password",

        confirmPassword:
            "Confirm password",

        createUser:
            "Create user",

        delete:
            "Delete",

        active:
            "Active",

        inactive:
            "Inactive",

        importOperation:
            "Purchase",

        saleOperation:
            "Sale",

        retailCustomer:
            "Retail customer",

        noData:
            "No data found",

        noLowStock:
            "No low-stock products",

        warehouseCreated:
            "Warehouse created",

        productCreated:
            "Product created",

        importCreated:
            "Purchase posted",

        saleCreated:
            "Sale completed",

        counterpartyCreated:
            "Counterparty created",

        userCreated:
            "User created",

        settingsSaved:
            "Settings saved",

        error:
            "Error",

        warehouseHasStock:
            "This warehouse still contains stock. Move or clear the stock first.",

        warehouseHasDocuments:
            "Purchase or sales documents already reference this warehouse. It cannot be deleted.",

        insufficientStock:
            "Insufficient stock in the selected warehouse.",

        passwordsMismatch:
            "Passwords do not match.",

        loginExists:
            "This login already exists.",

        warehouseCodeExists:
            "This warehouse code already exists.",

        deleteWarehouse:
            "Delete warehouse?",

        deleteProduct:
            "Delete product?",

        deleteCounterparty:
            "Delete counterparty?",

        deleteUser:
            "Delete user?",

        reportTitle:
            "Full warehouse and sales report",

        importReportTitle:
            "Purchase report",

        salesReportTitle:
            "Sales report",

        stockReportTitle:
            "Stock report",

        reportingPeriod:
            "Reporting period",

        reportWarehouse:
            "Report warehouse",

        reportCreated:
            "Report generated",

        importList:
            "Purchase list",

        salesList:
            "Sales list",

        stockList:
            "Stock balances",

        cost:
            "Cost",

        periodAll:
            "All time",

        dashboardSubtitle:
            "Main indicators for all warehouses",

        warehousesSubtitle:
            "Warehouse, capacity and stock management",

        stockSubtitle:
            "Product stock by warehouse",

        importsSubtitle:
            "Purchases and destination warehouses",

        salesSubtitle:
            "Sales and stock deduction by warehouse",

        productsSubtitle:
            "Product cards and warehouse balances",

        counterpartiesSubtitle:
            "Suppliers and buyers",

        reportsSubtitle:
            "Financial and warehouse analytics",

        usersSubtitle:
            "Accounts, roles and access",

        settingsSubtitle:
            "System and document parameters"
    }

};


/* =========================================================
   PAGE CONFIG
========================================================= */

const PAGE_CONFIG = {

    dashboard: {
        title: "dashboard",
        subtitle: "dashboardSubtitle"
    },

    warehouses: {
        title: "warehouses",
        subtitle: "warehousesSubtitle"
    },

    stock: {
        title: "stockBalances",
        subtitle: "stockSubtitle"
    },

    imports: {
        title: "imports",
        subtitle: "importsSubtitle"
    },

    sales: {
        title: "sales",
        subtitle: "salesSubtitle"
    },

    products: {
        title: "products",
        subtitle: "productsSubtitle"
    },

    counterparties: {
        title: "counterparties",
        subtitle: "counterpartiesSubtitle"
    },

    reports: {
        title: "reports",
        subtitle: "reportsSubtitle"
    },

    users: {
        title: "users",
        subtitle: "usersSubtitle"
    },

    settings: {
        title: "settings",
        subtitle: "settingsSubtitle"
    }

};


/* =========================================================
   CATEGORIES
========================================================= */

const CATEGORIES = [

    {
        uz: "Elektronika",
        ru: "Электроника",
        en: "Electronics",
        prefix: "EL",
        warehouseType: "electronics",

        subcategories: [
            "Smartfonlar",
            "Noutbuklar",
            "Planshetlar",
            "Monitorlar",
            "Printerlar",
            "Televizorlar",
            "Quloqchinlar",
            "Komplekt qismlar"
        ]
    },

    {
        uz: "Maishiy texnika",
        ru: "Бытовая техника",
        en: "Home appliances",
        prefix: "BT",
        warehouseType: "electronics",

        subcategories: [
            "Muzlatkichlar",
            "Kir yuvish mashinalari",
            "Konditsionerlar",
            "Changyutgichlar",
            "Mikroto‘lqinli pechlar"
        ]
    },

    {
        uz: "Kiyim",
        ru: "Одежда",
        en: "Clothing",
        prefix: "CL",
        warehouseType: "clothing",

        subcategories: [
            "Erkaklar kiyimi",
            "Ayollar kiyimi",
            "Bolalar kiyimi",
            "Sport kiyimi"
        ]
    },

    {
        uz: "Poyabzal",
        ru: "Обувь",
        en: "Footwear",
        prefix: "SH",
        warehouseType: "clothing",

        subcategories: [
            "Erkaklar poyabzali",
            "Ayollar poyabzali",
            "Bolalar poyabzali",
            "Sport poyabzali"
        ]
    },

    {
        uz: "Oziq-ovqat",
        ru: "Продукты",
        en: "Food",
        prefix: "FD",
        warehouseType: "food",

        subcategories: [
            "Ichimliklar",
            "Sut mahsulotlari",
            "Bakaleya",
            "Qandolat mahsulotlari",
            "Konservalar"
        ]
    },

    {
        uz: "Uy-ro‘zg‘or",
        ru: "Дом и хозяйство",
        en: "Home & household",
        prefix: "HM",
        warehouseType: "household",

        subcategories: [
            "Maishiy kimyo",
            "Idishlar",
            "Tekstil",
            "Xo‘jalik buyumlari"
        ]
    },

    {
        uz: "Kanselyariya",
        ru: "Канцелярия",
        en: "Stationery",
        prefix: "ST",
        warehouseType: "universal",

        subcategories: [
            "Qog‘oz",
            "Ruchkalar",
            "Daftarlar",
            "Ofis jihozlari"
        ]
    },

    {
        uz: "Mebel",
        ru: "Мебель",
        en: "Furniture",
        prefix: "FR",
        warehouseType: "universal",

        subcategories: [
            "Stollar",
            "Stullar",
            "Shkaflar",
            "Ofis mebeli"
        ]
    },

    {
        uz: "Kosmetika",
        ru: "Косметика",
        en: "Cosmetics",
        prefix: "CS",
        warehouseType: "universal",

        subcategories: [
            "Parfyumeriya",
            "Yuz parvarishi",
            "Tana parvarishi"
        ]
    },

    {
        uz: "Avtotovarlar",
        ru: "Автотовары",
        en: "Automotive",
        prefix: "AU",
        warehouseType: "universal",

        subcategories: [
            "Avto aksessuarlar",
            "Avto kimyo",
            "Avto elektronika"
        ]
    }

];


/* =========================================================
   DEFAULT WAREHOUSES
========================================================= */

const DEFAULT_WAREHOUSES = [

    {
        id: "WH-000001",

        code:
            "CENTRAL",

        name:
            "Markaziy ombor",

        type:
            "universal",

        manager:
            "Akmal Karimov",

        phone:
            "+998 71 200 10 10",

        address:
            "Toshkent shahri, Markaziy logistika hududi",

        area:
            1200,

        capacity:
            25000,

        temperature:
            "+10°C / +25°C",

        notes:
            "Universal mahsulotlar uchun asosiy ombor.",

        active:
            true
    },


    {
        id: "WH-000002",

        code:
            "TECH",

        name:
            "Texnika ombori",

        type:
            "electronics",

        manager:
            "Dilshod Raximov",

        phone:
            "+998 71 205 11 44",

        address:
            "Toshkent shahri, Texnopark hududi",

        area:
            850,

        capacity:
            8000,

        temperature:
            "+15°C / +25°C",

        notes:
            "Elektronika va maishiy texnika uchun.",

        active:
            true
    },


    {
        id: "WH-000003",

        code:
            "FOOD",

        name:
            "Oziq-ovqat ombori",

        type:
            "food",

        manager:
            "Sherzod Nasrullayev",

        phone:
            "+998 91 400 25 25",

        address:
            "Toshkent viloyati, logistika markazi",

        area:
            1000,

        capacity:
            40000,

        temperature:
            "+2°C / +18°C",

        notes:
            "Oziq-ovqat va ichimlik mahsulotlari.",

        active:
            true
    },


    {
        id: "WH-000004",

        code:
            "TEXTILE",

        name:
            "Kiyim-kechak ombori",

        type:
            "clothing",

        manager:
            "Doston Ergashev",

        phone:
            "+998 90 740 33 20",

        address:
            "Toshkent shahri, Sergeli tumani",

        area:
            720,

        capacity:
            18000,

        temperature:
            "+10°C / +25°C",

        notes:
            "Kiyim, tekstil va poyabzal mahsulotlari.",

        active:
            true
    },


    {
        id: "WH-000005",

        code:
            "HOUSE",

        name:
            "Uy-ro‘zg‘or ombori",

        type:
            "household",

        manager:
            "Javlon Qodirov",

        phone:
            "+998 90 444 22 11",

        address:
            "Toshkent shahri, Bektemir tumani",

        area:
            600,

        capacity:
            15000,

        temperature:
            "+5°C / +28°C",

        notes:
            "Maishiy kimyo va uy-ro‘zg‘or mahsulotlari.",

        active:
            true
    }

];


/* =========================================================
   SETTINGS
========================================================= */

const DEFAULT_SETTINGS = {
    companyName: "StoreFlow Market",
    inn: "",
    phone: "",
    address: "",
    currency: "so'm",
    importPrefix: "IMP",
    salePrefix: "EXP",
    lowStock: 5
};


/* =========================================================
   COUNTERPARTIES
========================================================= */

const DEFAULT_COUNTERPARTIES = [

    seedCounterparty(
        "CTR-000001",
        "Orient Trade LLC",
        "supplier",
        "309456781",
        "+998 71 200 10 01",
        "Akmal Karimov",
        "Toshkent shahri"
    ),

    seedCounterparty(
        "CTR-000002",
        "Global Electronics",
        "supplier",
        "307245981",
        "+998 71 205 11 44",
        "Dilshod Raximov",
        "Toshkent shahri"
    ),

    seedCounterparty(
        "CTR-000003",
        "Asia Distribution",
        "supplier",
        "308741255",
        "+998 90 701 22 11",
        "Sardor Aliyev",
        "Toshkent shahri"
    ),

    seedCounterparty(
        "CTR-000004",
        "Techno Import LLC",
        "supplier",
        "305965411",
        "+998 71 230 22 15",
        "Javlon Qodirov",
        "Toshkent shahri"
    ),

    seedCounterparty(
        "CTR-000005",
        "Smart Market Supply",
        "supplier",
        "309047612",
        "+998 93 510 44 55",
        "Azizbek Xasanov",
        "Samarqand shahri"
    ),

    seedCounterparty(
        "CTR-000006",
        "Uz Textile Trade",
        "supplier",
        "302114598",
        "+998 90 740 33 20",
        "Doston Ergashev",
        "Namangan shahri"
    ),

    seedCounterparty(
        "CTR-000007",
        "Fresh Food Supply",
        "supplier",
        "305414887",
        "+998 91 400 25 25",
        "Sherzod Nasrullayev",
        "Toshkent viloyati"
    ),

    seedCounterparty(
        "CTR-000008",
        "Premium Home Appliances",
        "supplier",
        "307554921",
        "+998 71 202 41 10",
        "Bekzod Umarov",
        "Toshkent shahri"
    ),

    seedCounterparty(
        "CTR-000009",
        "Baraka Distribution",
        "both",
        "308001245",
        "+998 90 909 77 11",
        "Ulugbek Rustamov",
        "Buxoro shahri"
    ),

    seedCounterparty(
        "CTR-000010",
        "Mega Import Group",
        "supplier",
        "304321784",
        "+998 71 220 50 10",
        "Kamron Yusupov",
        "Toshkent shahri"
    ),

    seedCounterparty(
        "CTR-000011",
        "Universal Trade",
        "both",
        "307652901",
        "+998 90 522 44 11",
        "Saidbek Muradov",
        "Termiz shahri"
    ),

    seedCounterparty(
        "CTR-000012",
        "Office Market",
        "supplier",
        "305789611",
        "+998 71 244 35 15",
        "Bobur Juraev",
        "Toshkent shahri"
    ),

    seedCounterparty(
        "CTR-000013",
        "Samarkand Textile",
        "supplier",
        "301887452",
        "+998 93 340 10 11",
        "Jasur Ismoilov",
        "Samarqand shahri"
    ),

    seedCounterparty(
        "CTR-000014",
        "Termiz Retail Group",
        "buyer",
        "309785423",
        "+998 90 777 15 15",
        "Alisher Tursunov",
        "Termiz shahri"
    ),

    seedCounterparty(
        "CTR-000015",
        "Family Market",
        "buyer",
        "307114225",
        "+998 91 300 99 88",
        "Rustam Xolmatov",
        "Denov shahri"
    )

];


function seedCounterparty(
    id,
    name,
    type,
    inn,
    phone,
    contact,
    address
) {

    return {
        id,
        name,
        type,
        inn,
        phone,
        contact,
        address,

        email: "",
        bank: "",

        active: true
    };

}


/* =========================================================
   DEFAULT PRODUCTS
========================================================= */

const DEFAULT_PRODUCTS = [

    seedProduct(
        "PRD-000001",
        "EL-000001",
        "Samsung Galaxy S26 Ultra",
        "Elektronika",
        "Smartfonlar",
        "Samsung",
        12500000,
        14900000,
        "WH-000002",
        8,
        4,
        "шт.",
        "T-01-01"
    ),

    seedProduct(
        "PRD-000002",
        "EL-000002",
        "Apple MacBook Air 15",
        "Elektronika",
        "Noutbuklar",
        "Apple",
        14500000,
        16900000,
        "WH-000002",
        5,
        3,
        "шт.",
        "T-01-02"
    ),

    seedProduct(
        "PRD-000003",
        "EL-000003",
        "HP LaserJet Pro M404",
        "Elektronika",
        "Printerlar",
        "HP",
        3900000,
        4650000,
        "WH-000002",
        12,
        5,
        "шт.",
        "T-02-01"
    ),

    seedProduct(
        "PRD-000004",
        "BT-000001",
        "LG Refrigerator 450L",
        "Maishiy texnika",
        "Muzlatkichlar",
        "LG",
        7600000,
        9100000,
        "WH-000002",
        3,
        4,
        "шт.",
        "T-10-01"
    ),

    seedProduct(
        "PRD-000005",
        "BT-000002",
        "Artel Washing Machine 8kg",
        "Maishiy texnika",
        "Kir yuvish mashinalari",
        "Artel",
        4300000,
        5250000,
        "WH-000002",
        9,
        3,
        "шт.",
        "T-10-02"
    ),

    seedProduct(
        "PRD-000006",
        "CL-000001",
        "Classic Shirt",
        "Kiyim",
        "Erkaklar kiyimi",
        "Classic",
        180000,
        260000,
        "WH-000004",
        35,
        10,
        "шт.",
        "K-02-01"
    ),

    seedProduct(
        "PRD-000007",
        "SH-000001",
        "Urban Runner",
        "Poyabzal",
        "Sport poyabzali",
        "Urban",
        320000,
        450000,
        "WH-000004",
        18,
        6,
        "шт.",
        "K-05-04"
    ),

    seedProduct(
        "PRD-000008",
        "FD-000001",
        "Coca-Cola 1.5L",
        "Oziq-ovqat",
        "Ichimliklar",
        "Coca-Cola",
        12000,
        16000,
        "WH-000003",
        120,
        30,
        "шт.",
        "F-02-01"
    ),

    seedProduct(
        "PRD-000009",
        "HM-000001",
        "Ariel 3kg",
        "Uy-ro‘zg‘or",
        "Maishiy kimyo",
        "Ariel",
        86000,
        110000,
        "WH-000005",
        22,
        8,
        "шт.",
        "H-01-03"
    ),

    seedProduct(
        "PRD-000010",
        "ST-000001",
        "Double A A4 80g",
        "Kanselyariya",
        "Qog‘oz",
        "Double A",
        55000,
        70000,
        "WH-000001",
        44,
        10,
        "упак.",
        "C-01-02"
    )

];


function seedProduct(
    id,
    sku,
    name,
    category,
    subcategory,
    brand,
    purchasePrice,
    salePrice,
    warehouseId,
    stock,
    minStock,
    unit,
    location
) {

    const markup =
        purchasePrice
        ?
        (
            (
                salePrice -
                purchasePrice
            )
            /
            purchasePrice
            *
            100
        )
        :
        0;


    return {

        id,
        sku,
        name,
        category,
        subcategory,
        brand,

        model: "",
        barcode: "",

        purchasePrice,
        salePrice,

        markup:
            Number(
                markup.toFixed(2)
            ),

        stockByWarehouse: {
            [warehouseId]:
                stock
        },

        defaultWarehouseId:
            warehouseId,

        stock,

        minStock,
        unit,
        location,

        photo: ""
    };

}


/* =========================================================
   STATE
========================================================= */

let currentUser = null;

let warehouses = [];
let products = [];
let counterparties = [];
let imports = [];
let sales = [];
let settings = {};

let currentSection =
    "dashboard";


let currentLanguage =
    localStorage.getItem(
        STORAGE.language
    )
    ||
    "uz";


let productPhotoData =
    "";


let importPhotoData =
    "";


let confirmCallback =
    null;


let importReportFilter = {
    period: "all",
    from: "",
    to: ""
};


let salesReportFilter = {
    period: "all",
    from: "",
    to: ""
};


/* =========================================================
   INIT
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    initializeApp
);


function initializeApp() {

    currentUser =
        getSession();


    if (!currentUser) {

        window.location.href =
            "login.html";

        return;

    }


    initializeStorage();

    loadApplicationData();

    migrateOldData();

    initializeTheme();

    setupUser();

    setupNavigation();

    setupHeader();

    setupLanguage();

    setupModals();

    setupForms();

    setupFilters();

    setupPeriodReports();

    setupCalculations();

    setupPhotoUploads();

    populateBaseSelects();

    setupReportDates();

    applyLanguage();

    renderAll();

}


/* =========================================================
   SESSION
========================================================= */

function getSession() {

    const raw =
        localStorage.getItem(
            STORAGE.session
        )
        ||
        sessionStorage.getItem(
            STORAGE.tempSession
        );


    if (!raw) {
        return null;
    }


    try {

        const data =
            JSON.parse(raw);


        return data.loggedIn
            ?
            data
            :
            null;

    } catch {

        return null;

    }

}


/* =========================================================
   STORAGE INIT
========================================================= */

function initializeStorage() {

    if (
        !localStorage.getItem(
            STORAGE.warehouses
        )
    ) {

        save(
            STORAGE.warehouses,
            DEFAULT_WAREHOUSES
        );

    }


    if (
        !localStorage.getItem(
            STORAGE.products
        )
    ) {

        save(
            STORAGE.products,
            DEFAULT_PRODUCTS
        );

    }


    if (
        !localStorage.getItem(
            STORAGE.counterparties
        )
    ) {

        save(
            STORAGE.counterparties,
            DEFAULT_COUNTERPARTIES
        );

    }


    if (
        !localStorage.getItem(
            STORAGE.imports
        )
    ) {

        save(
            STORAGE.imports,
            createDefaultImports()
        );

    }


    if (
        !localStorage.getItem(
            STORAGE.sales
        )
    ) {

        save(
            STORAGE.sales,
            createDefaultSales()
        );

    }


    if (
        !localStorage.getItem(
            STORAGE.settings
        )
    ) {

        save(
            STORAGE.settings,
            DEFAULT_SETTINGS
        );

    }

}


/* =========================================================
   DEFAULT DOCUMENTS
========================================================= */

function createDefaultImports() {

    return [

        {
            id:
                "IMP-2026-000001",

            date:
                daysAgo(1),

            warehouseId:
                "WH-000002",

            warehouseName:
                "Texnika ombori",

            counterpartyId:
                "CTR-000002",

            counterpartyName:
                "Global Electronics",

            supplierInvoice:
                "GE-10451",

            productId:
                "PRD-000001",

            sku:
                "EL-000001",

            productName:
                "Samsung Galaxy S26 Ultra",

            category:
                "Elektronika",

            quantity:
                8,

            purchasePrice:
                12500000,

            salePrice:
                14900000,

            totalPurchase:
                100000000,

            totalRetail:
                119200000,

            userName:
                "Administrator",

            createdAt:
                new Date()
                .toISOString()
        },


        {
            id:
                "IMP-2026-000002",

            date:
                daysAgo(3),

            warehouseId:
                "WH-000003",

            warehouseName:
                "Oziq-ovqat ombori",

            counterpartyId:
                "CTR-000007",

            counterpartyName:
                "Fresh Food Supply",

            supplierInvoice:
                "FF-445",

            productId:
                "PRD-000008",

            sku:
                "FD-000001",

            productName:
                "Coca-Cola 1.5L",

            category:
                "Oziq-ovqat",

            quantity:
                120,

            purchasePrice:
                12000,

            salePrice:
                16000,

            totalPurchase:
                1440000,

            totalRetail:
                1920000,

            userName:
                "Administrator",

            createdAt:
                new Date()
                .toISOString()
        }

    ];

}


function createDefaultSales() {

    return [

        {
            id:
                "EXP-2026-000001",

            date:
                today(),

            warehouseId:
                "WH-000003",

            warehouseName:
                "Oziq-ovqat ombori",

            productId:
                "PRD-000008",

            sku:
                "FD-000001",

            productName:
                "Coca-Cola 1.5L",

            category:
                "Oziq-ovqat",

            quantity:
                6,

            purchasePrice:
                12000,

            salePrice:
                16000,

            discount:
                0,

            total:
                96000,

            cost:
                72000,

            profit:
                24000,

            buyerName:
                "Retail customer",

            userName:
                "Administrator"
        },


        {
            id:
                "EXP-2026-000002",

            date:
                daysAgo(1),

            warehouseId:
                "WH-000002",

            warehouseName:
                "Texnika ombori",

            productId:
                "PRD-000003",

            sku:
                "EL-000003",

            productName:
                "HP LaserJet Pro M404",

            category:
                "Elektronika",

            quantity:
                1,

            purchasePrice:
                3900000,

            salePrice:
                4650000,

            discount:
                0,

            total:
                4650000,

            cost:
                3900000,

            profit:
                750000,

            buyerName:
                "Termiz Retail Group",

            userName:
                "Administrator"
        }

    ];

}


/* =========================================================
   LOAD
========================================================= */

function loadApplicationData() {

    warehouses =
        load(
            STORAGE.warehouses,
            []
        );


    products =
        load(
            STORAGE.products,
            []
        );


    counterparties =
        load(
            STORAGE.counterparties,
            []
        );


    imports =
        load(
            STORAGE.imports,
            []
        );


    sales =
        load(
            STORAGE.sales,
            []
        );


    settings =
        load(
            STORAGE.settings,
            DEFAULT_SETTINGS
        );

}


function load(
    key,
    fallback
) {

    try {

        const raw =
            localStorage.getItem(key);


        return raw
            ?
            JSON.parse(raw)
            :
            fallback;

    } catch {

        return fallback;

    }

}


function save(
    key,
    value
) {

    localStorage.setItem(
        key,
        JSON.stringify(value)
    );

}


/* =========================================================
   MIGRATION FROM OLD SINGLE-WAREHOUSE DATA
========================================================= */

function migrateOldData() {

    let productChanged =
        false;


    products.forEach(
        product => {

            if (
                !product.stockByWarehouse
                ||
                typeof product.stockByWarehouse
                !==
                "object"
            ) {

                const warehouse =
                    suggestedWarehouseForCategory(
                        product.category
                    );


                product.stockByWarehouse = {
                    [warehouse.id]:
                        Number(
                            product.stock
                            ||
                            0
                        )
                };


                product.defaultWarehouseId =
                    warehouse.id;


                productChanged =
                    true;

            }


            if (
                !product.defaultWarehouseId
            ) {

                const ids =
                    Object.keys(
                        product.stockByWarehouse
                        ||
                        {}
                    );


                product.defaultWarehouseId =
                    ids[0]
                    ||
                    suggestedWarehouseForCategory(
                        product.category
                    ).id;


                productChanged =
                    true;

            }


            syncLegacyStock(
                product
            );

        }
    );


    let importChanged =
        false;


    imports.forEach(
        item => {

            if (
                !item.warehouseId
            ) {

                const warehouse =
                    suggestedWarehouseForCategory(
                        item.category
                    );


                item.warehouseId =
                    warehouse.id;


                item.warehouseName =
                    warehouse.name;


                importChanged =
                    true;

            }


            if (
                !item.warehouseName
            ) {

                item.warehouseName =
                    warehouseName(
                        item.warehouseId
                    );


                importChanged =
                    true;

            }

        }
    );


    let salesChanged =
        false;


    sales.forEach(
        item => {

            if (
                !item.warehouseId
            ) {

                const warehouse =
                    suggestedWarehouseForCategory(
                        item.category
                    );


                item.warehouseId =
                    warehouse.id;


                item.warehouseName =
                    warehouse.name;


                salesChanged =
                    true;

            }


            if (
                !item.warehouseName
            ) {

                item.warehouseName =
                    warehouseName(
                        item.warehouseId
                    );


                salesChanged =
                    true;

            }

        }
    );


    if (
        productChanged
    ) {

        save(
            STORAGE.products,
            products
        );

    }


    if (
        importChanged
    ) {

        save(
            STORAGE.imports,
            imports
        );

    }


    if (
        salesChanged
    ) {

        save(
            STORAGE.sales,
            sales
        );

    }

}


/* =========================================================
   THEME
========================================================= */

function initializeTheme() {

    const theme =
        localStorage.getItem(
            STORAGE.theme
        );


    if (
        theme ===
        "dark"
    ) {

        document.body.classList.add(
            "dark-mode"
        );

    }


    document
        .getElementById(
            "themeToggle"
        )
        .addEventListener(
            "click",
            () => {

                document.body
                    .classList
                    .toggle(
                        "dark-mode"
                    );


                localStorage.setItem(
                    STORAGE.theme,
                    document.body
                        .classList
                        .contains(
                            "dark-mode"
                        )
                    ?
                    "dark"
                    :
                    "light"
                );

            }
        );

}


/* =========================================================
   USER
========================================================= */

function setupUser() {

    const name =
        currentUser.fullName
        ||
        currentUser.username
        ||
        "User";


    const role =
        currentUser.roleName
        ||
        currentUser.role
        ||
        "";


    const initials =
        getInitials(
            name
        );


    [
        "headerUserName",
        "sidebarUserName",
        "dropdownUserName"
    ]
    .forEach(
        id =>
            setText(
                id,
                name
            )
    );


    [
        "headerUserRole",
        "sidebarUserRole",
        "dropdownUserRole"
    ]
    .forEach(
        id =>
            setText(
                id,
                role
            )
    );


    [
        "headerAvatar",
        "sidebarAvatar"
    ]
    .forEach(
        id =>
            setText(
                id,
                initials
            )
    );


    setText(
        "welcomeUser",
        firstName(
            name
        )
    );

}


/* =========================================================
   HEADER
========================================================= */

function setupHeader() {

    const userButton =
        document.getElementById(
            "userButton"
        );


    const userDropdown =
        document.getElementById(
            "userDropdown"
        );


    userButton.addEventListener(
        "click",
        event => {

            event.stopPropagation();


            userDropdown
                .classList
                .toggle(
                    "show"
                );

        }
    );


    document.addEventListener(
        "click",
        () => {

            userDropdown
                .classList
                .remove(
                    "show"
                );


            document
                .getElementById(
                    "languageDropdown"
                )
                .classList
                .remove(
                    "show"
                );

        }
    );


    document
        .getElementById(
            "logoutButton"
        )
        .addEventListener(
            "click",
            logout
        );


    document
        .getElementById(
            "globalSearch"
        )
        .addEventListener(
            "keydown",
            event => {

                if (
                    event.key !==
                    "Enter"
                ) {

                    return;

                }


                openSection(
                    "products"
                );


                setValue(
                    "productsSearch",
                    event.target.value
                );


                renderProducts();

            }
        );

}


/* =========================================================
   LANGUAGE
========================================================= */

function setupLanguage() {

    const button =
        document.getElementById(
            "languageButton"
        );


    const dropdown =
        document.getElementById(
            "languageDropdown"
        );


    button.addEventListener(
        "click",
        event => {

            event.stopPropagation();


            dropdown.classList.toggle(
                "show"
            );

        }
    );


    dropdown
        .querySelectorAll(
            "[data-lang]"
        )
        .forEach(
            item => {

                item.addEventListener(
                    "click",
                    () => {

                        currentLanguage =
                            item.dataset.lang;


                        localStorage.setItem(
                            STORAGE.language,
                            currentLanguage
                        );


                        dropdown.classList.remove(
                            "show"
                        );


                        applyLanguage();

                    }
                );

            }
        );

}


function t(
    key
) {

    return (
        I18N[currentLanguage]?.[key]
        ||
        I18N.uz[key]
        ||
        key
    );

}


function applyLanguage() {

    document.documentElement.lang =
        currentLanguage;


    document
        .querySelectorAll(
            "[data-i18n]"
        )
        .forEach(
            element => {

                element.textContent =
                    t(
                        element.dataset.i18n
                    );

            }
        );


    document
        .querySelectorAll(
            "[data-i18n-placeholder]"
        )
        .forEach(
            element => {

                element.placeholder =
                    t(
                        element.dataset
                            .i18nPlaceholder
                    );

            }
        );


    const labels = {
        uz: "O‘Z",
        ru: "RU",
        en: "EN"
    };


    setText(
        "currentLanguage",
        labels[currentLanguage]
    );


    updatePageHeading();

    populateDynamicSelects();

    renderAll();

}


/* =========================================================
   LOGOUT
========================================================= */

function logout() {

    localStorage.removeItem(
        STORAGE.session
    );


    sessionStorage.removeItem(
        STORAGE.tempSession
    );


    window.location.href =
        "login.html";

}


/* =========================================================
   NAVIGATION
========================================================= */

function setupNavigation() {

    document
        .querySelectorAll(
            ".menu-item[data-section]"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    () => {

                        openSection(
                            button.dataset.section
                        );

                    }
                );

            }
        );


    document
        .querySelectorAll(
            "[data-section-link]"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    () => {

                        openSection(
                            button.dataset.sectionLink
                        );

                    }
                );

            }
        );


    document
        .getElementById(
            "mobileMenu"
        )
        .addEventListener(
            "click",
            openSidebar
        );


    document
        .getElementById(
            "sidebarClose"
        )
        .addEventListener(
            "click",
            closeSidebar
        );


    document
        .getElementById(
            "sidebarOverlay"
        )
        .addEventListener(
            "click",
            closeSidebar
        );

}


function openSection(
    sectionName
) {

    currentSection =
        sectionName;


    document
        .querySelectorAll(
            ".menu-item"
        )
        .forEach(
            item =>
                item.classList.remove(
                    "active"
                )
        );


    const menu =
        document.querySelector(
            `.menu-item[data-section="${sectionName}"]`
        );


    if (
        menu
    ) {

        menu.classList.add(
            "active"
        );

    }


    document
        .querySelectorAll(
            ".app-section"
        )
        .forEach(
            section =>
                section.classList.remove(
                    "active"
                )
        );


    const target =
        document.getElementById(
            `section-${sectionName}`
        );


    if (
        target
    ) {

        target.classList.add(
            "active"
        );

    }


    updatePageHeading();

    closeSidebar();

}


function updatePageHeading() {

    const config =
        PAGE_CONFIG[
            currentSection
        ];


    if (
        !config
    ) {

        return;

    }


    setText(
        "pageTitle",
        t(
            config.title
        )
    );


    setText(
        "pageSubtitle",
        t(
            config.subtitle
        )
    );

}


function openSidebar() {

    document
        .getElementById(
            "sidebar"
        )
        .classList.add(
            "show"
        );


    document
        .getElementById(
            "sidebarOverlay"
        )
        .classList.add(
            "show"
        );

}


function closeSidebar() {

    document
        .getElementById(
            "sidebar"
        )
        .classList.remove(
            "show"
        );


    document
        .getElementById(
            "sidebarOverlay"
        )
        .classList.remove(
            "show"
        );

}


/* =========================================================
   MODALS
========================================================= */

function setupModals() {

    document
        .querySelectorAll(
            "[data-open-modal]"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    () => {

                        openModal(
                            button.dataset
                                .openModal
                        );

                    }
                );

            }
        );


    document
        .querySelectorAll(
            "[data-close-modal]"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    () => {

                        const modal =
                            button.closest(
                                ".modal"
                            );


                        if (
                            modal
                        ) {

                            closeModal(
                                modal.id
                            );

                        }

                    }
                );

            }
        );


    document.addEventListener(
        "keydown",
        event => {

            if (
                event.key ===
                "Escape"
            ) {

                document
                    .querySelectorAll(
                        ".modal.show"
                    )
                    .forEach(
                        modal =>
                            closeModal(
                                modal.id
                            )
                    );

            }

        }
    );


    document
        .getElementById(
            "confirmCancel"
        )
        .addEventListener(
            "click",
            () => {

                confirmCallback =
                    null;


                closeModal(
                    "confirmModal"
                );

            }
        );


    document
        .getElementById(
            "confirmAccept"
        )
        .addEventListener(
            "click",
            () => {

                if (
                    typeof confirmCallback
                    ===
                    "function"
                ) {

                    confirmCallback();

                }


                confirmCallback =
                    null;


                closeModal(
                    "confirmModal"
                );

            }
        );

}


function openModal(
    id
) {

    if (
        id ===
        "warehouseModal"
    ) {

        prepareWarehouseModal();

    }


    if (
        id ===
        "productModal"
    ) {

        prepareProductModal();

    }


    if (
        id ===
        "importModal"
    ) {

        prepareImportModal();

    }


    if (
        id ===
        "saleModal"
    ) {

        prepareSaleModal();

    }


    const modal =
        document.getElementById(
            id
        );


    if (
        !modal
    ) {

        return;

    }


    modal.classList.add(
        "show"
    );


    document.body.style.overflow =
        "hidden";

}


function closeModal(
    id
) {

    const modal =
        document.getElementById(
            id
        );


    if (
        !modal
    ) {

        return;

    }


    modal.classList.remove(
        "show"
    );


    if (
        !document.querySelector(
            ".modal.show"
        )
    ) {

        document.body.style.overflow =
            "";

    }

}


/* =========================================================
   FORMS
========================================================= */

function setupForms() {

    document
        .getElementById(
            "warehouseForm"
        )
        .addEventListener(
            "submit",
            createWarehouse
        );


    document
        .getElementById(
            "productForm"
        )
        .addEventListener(
            "submit",
            createProduct
        );


    document
        .getElementById(
            "importForm"
        )
        .addEventListener(
            "submit",
            createImport
        );


    document
        .getElementById(
            "saleForm"
        )
        .addEventListener(
            "submit",
            createSale
        );


    document
        .getElementById(
            "counterpartyForm"
        )
        .addEventListener(
            "submit",
            createCounterparty
        );


    document
        .getElementById(
            "userForm"
        )
        .addEventListener(
            "submit",
            createUser
        );


    document
        .getElementById(
            "settingsForm"
        )
        .addEventListener(
            "submit",
            saveSettings
        );


    document
        .getElementById(
            "printStockReport"
        )
        .addEventListener(
            "click",
            printStockReport
        );


    document
        .getElementById(
            "printImportsReport"
        )
        .addEventListener(
            "click",
            printImportsReport
        );


    document
        .getElementById(
            "printSalesReport"
        )
        .addEventListener(
            "click",
            printSalesReport
        );


    document
        .getElementById(
            "printFullReport"
        )
        .addEventListener(
            "click",
            printFullReport
        );


    document
        .getElementById(
            "applyFullReport"
        )
        .addEventListener(
            "click",
            renderReports
        );

}


/* =========================================================
   FILTERS
========================================================= */

function setupFilters() {

    bindInput(
        "warehousesSearch",
        renderWarehouses
    );


    bindChange(
        "warehouseTypeFilter",
        renderWarehouses
    );


    bindInput(
        "stockSearch",
        renderStock
    );


    bindChange(
        "stockWarehouseFilter",
        renderStock
    );


    bindChange(
        "stockCategoryFilter",
        renderStock
    );


    bindChange(
        "stockStatusFilter",
        renderStock
    );


    bindInput(
        "importsSearch",
        renderImports
    );


    bindChange(
        "importsWarehouseFilter",
        renderImports
    );


    bindInput(
        "salesSearch",
        renderSales
    );


    bindChange(
        "salesWarehouseFilter",
        renderSales
    );


    bindInput(
        "productsSearch",
        renderProducts
    );


    bindChange(
        "productsWarehouseFilter",
        renderProducts
    );


    bindChange(
        "productsCategoryFilter",
        renderProducts
    );


    bindInput(
        "counterpartiesSearch",
        renderCounterparties
    );


    bindChange(
        "counterpartyTypeFilter",
        renderCounterparties
    );


    bindInput(
        "usersSearch",
        renderUsers
    );


    bindChange(
        "reportWarehouseFilter",
        renderReports
    );

}


/* =========================================================
   PERIOD REPORTS
========================================================= */

function setupPeriodReports() {

    document
        .querySelectorAll(
            ".period-presets"
        )
        .forEach(
            group => {

                group
                    .querySelectorAll(
                        ".period-button"
                    )
                    .forEach(
                        button => {

                            button.addEventListener(
                                "click",
                                () => {

                                    group
                                        .querySelectorAll(
                                            ".period-button"
                                        )
                                        .forEach(
                                            item =>
                                                item.classList.remove(
                                                    "active"
                                                )
                                        );


                                    button.classList.add(
                                        "active"
                                    );


                                    applyPeriodPreset(
                                        group.dataset.reportGroup,
                                        button.dataset.period
                                    );

                                }
                            );

                        }
                    );

            }
        );


    document
        .getElementById(
            "applyImportsPeriod"
        )
        .addEventListener(
            "click",
            () => {

                clearPeriodButtons(
                    "imports"
                );


                importReportFilter = {
                    period: "custom",

                    from:
                        valueOf(
                            "importsFrom"
                        ),

                    to:
                        valueOf(
                            "importsTo"
                        )
                };


                renderImports();

            }
        );


    document
        .getElementById(
            "applySalesPeriod"
        )
        .addEventListener(
            "click",
            () => {

                clearPeriodButtons(
                    "sales"
                );


                salesReportFilter = {
                    period: "custom",

                    from:
                        valueOf(
                            "salesFrom"
                        ),

                    to:
                        valueOf(
                            "salesTo"
                        )
                };


                renderSales();

            }
        );

}


function clearPeriodButtons(
    type
) {

    const group =
        document.querySelector(
            `.period-presets[data-report-group="${type}"]`
        );


    group
        ?.querySelectorAll(
            ".period-button"
        )
        .forEach(
            button =>
                button.classList.remove(
                    "active"
                )
        );

}


function applyPeriodPreset(
    type,
    period
) {

    const range =
        getPeriodRange(
            period
        );


    if (
        type ===
        "imports"
    ) {

        importReportFilter = {
            period,
            from: range.from,
            to: range.to
        };


        setValue(
            "importsFrom",
            range.from
        );


        setValue(
            "importsTo",
            range.to
        );


        renderImports();

    }


    if (
        type ===
        "sales"
    ) {

        salesReportFilter = {
            period,
            from: range.from,
            to: range.to
        };


        setValue(
            "salesFrom",
            range.from
        );


        setValue(
            "salesTo",
            range.to
        );


        renderSales();

    }

}


function getPeriodRange(
    period
) {

    const end =
        new Date();


    end.setHours(
        12,
        0,
        0,
        0
    );


    if (
        period ===
        "all"
    ) {

        return {
            from: "",
            to: ""
        };

    }


    if (
        period ===
        "today"
    ) {

        const day =
            isoDate(
                end
            );


        return {
            from: day,
            to: day
        };

    }


    if (
        period ===
        "7days"
    ) {

        const start =
            new Date(
                end
            );


        start.setDate(
            start.getDate() -
            6
        );


        return {
            from: isoDate(start),
            to: isoDate(end)
        };

    }


    if (
        period ===
        "30days"
    ) {

        const start =
            new Date(
                end
            );


        start.setDate(
            start.getDate() -
            29
        );


        return {
            from: isoDate(start),
            to: isoDate(end)
        };

    }


    if (
        period ===
        "month"
    ) {

        const start =
            new Date(
                end.getFullYear(),
                end.getMonth(),
                1,
                12
            );


        return {
            from: isoDate(start),
            to: isoDate(end)
        };

    }


    return {
        from: "",
        to: ""
    };

}


/* =========================================================
   CALCULATIONS
========================================================= */

function setupCalculations() {

    bindChange(
        "productCategory",
        handleProductCategoryChange
    );


    bindInput(
        "productPurchasePrice",
        calculateProductSalePrice
    );


    bindInput(
        "productMarkup",
        calculateProductSalePrice
    );


    bindInput(
        "productSalePrice",
        calculateProductMarkup
    );


    bindChange(
        "importCategory",
        handleImportCategoryChange
    );


    [
        "importQuantity",
        "importPurchasePrice",
        "importMarkup"
    ]
    .forEach(
        id =>
            bindInput(
                id,
                calculateImportSalePrice
            )
    );


    bindInput(
        "importSalePrice",
        calculateImportMarkup
    );


    bindChange(
        "saleWarehouse",
        () => {

            populateSaleProductSelect();

            updateSaleProductInfo();

        }
    );


    bindChange(
        "saleProduct",
        updateSaleProductInfo
    );


    [
        "saleQuantity",
        "salePrice",
        "saleDiscount"
    ]
    .forEach(
        id =>
            bindInput(
                id,
                calculateSale
            )
    );

}


function handleProductCategoryChange() {

    const category =
        valueOf(
            "productCategory"
        );


    populateSubcategories(
        category,
        "productSubcategory"
    );


    setValue(
        "productSku",
        generateSku(
            category
        )
    );


    const suggested =
        suggestedWarehouseForCategory(
            category
        );


    setValue(
        "productWarehouse",
        suggested.id
    );

}


function handleImportCategoryChange() {

    const category =
        valueOf(
            "importCategory"
        );


    populateSubcategories(
        category,
        "importSubcategory"
    );


    setValue(
        "importSku",
        generateSku(
            category
        )
    );


    const suggested =
        suggestedWarehouseForCategory(
            category
        );


    setValue(
        "importWarehouse",
        suggested.id
    );

}


/* =========================================================
   PHOTOS
========================================================= */

function setupPhotoUploads() {

    document
        .getElementById(
            "productPhoto"
        )
        .addEventListener(
            "change",
            async event => {

                const file =
                    event.target
                        .files?.[0];


                if (
                    !file
                ) {

                    return;

                }


                try {

                    productPhotoData =
                        await compressImage(
                            file
                        );


                    renderPhotoPreview(
                        "productPhotoPreview",
                        productPhotoData
                    );

                } catch {

                    showToast(
                        t("error"),
                        "Image error",
                        "error"
                    );

                }

            }
        );


    document
        .getElementById(
            "importPhoto"
        )
        .addEventListener(
            "change",
            async event => {

                const file =
                    event.target
                        .files?.[0];


                if (
                    !file
                ) {

                    return;

                }


                try {

                    importPhotoData =
                        await compressImage(
                            file
                        );


                    renderPhotoPreview(
                        "importPhotoPreview",
                        importPhotoData
                    );

                } catch {

                    showToast(
                        t("error"),
                        "Image error",
                        "error"
                    );

                }

            }
        );

}


function compressImage(
    file,
    maxSize = 700,
    quality = .75
) {

    return new Promise(
        (
            resolve,
            reject
        ) => {

            const reader =
                new FileReader();


            reader.onload =
                () => {

                    const image =
                        new Image();


                    image.onload =
                        () => {

                            let width =
                                image.width;


                            let height =
                                image.height;


                            if (
                                width >
                                maxSize
                                ||
                                height >
                                maxSize
                            ) {

                                const ratio =
                                    Math.min(
                                        maxSize / width,
                                        maxSize / height
                                    );


                                width =
                                    Math.round(
                                        width *
                                        ratio
                                    );


                                height =
                                    Math.round(
                                        height *
                                        ratio
                                    );

                            }


                            const canvas =
                                document.createElement(
                                    "canvas"
                                );


                            canvas.width =
                                width;


                            canvas.height =
                                height;


                            const context =
                                canvas.getContext(
                                    "2d"
                                );


                            context.drawImage(
                                image,
                                0,
                                0,
                                width,
                                height
                            );


                            resolve(
                                canvas.toDataURL(
                                    "image/jpeg",
                                    quality
                                )
                            );

                        };


                    image.onerror =
                        reject;


                    image.src =
                        reader.result;

                };


            reader.onerror =
                reject;


            reader.readAsDataURL(
                file
            );

        }
    );

}


function renderPhotoPreview(
    id,
    image
) {

    const preview =
        document.getElementById(
            id
        );


    if (
        !image
    ) {

        preview.innerHTML =
            `
            <svg>
                <use href="#i-image"></use>
            </svg>

            <span>
                ${escapeHtml(t("noPhoto"))}
            </span>
            `;

        return;

    }


    preview.innerHTML =
        `
        <img
            src="${image}"
            alt=""
        >
        `;

}


/* =========================================================
   SELECTS
========================================================= */

function populateBaseSelects() {

    populateCategorySelect(
        "productCategory"
    );


    populateCategorySelect(
        "importCategory"
    );


    populateDynamicSelects();

}


function populateDynamicSelects() {

    populateWarehouseFilter(
        "stockWarehouseFilter"
    );


    populateWarehouseFilter(
        "importsWarehouseFilter"
    );


    populateWarehouseFilter(
        "salesWarehouseFilter"
    );


    populateWarehouseFilter(
        "productsWarehouseFilter"
    );


    populateWarehouseFilter(
        "reportWarehouseFilter"
    );


    populateWarehouseFormSelect(
        "productWarehouse"
    );


    populateWarehouseFormSelect(
        "importWarehouse"
    );


    populateWarehouseFormSelect(
        "saleWarehouse"
    );


    populateCategoryFilter(
        "stockCategoryFilter"
    );


    populateCategoryFilter(
        "productsCategoryFilter"
    );


    populateCounterpartySelects();

    populateSaleProductSelect();

}


function populateWarehouseFilter(
    id
) {

    const select =
        document.getElementById(
            id
        );


    if (
        !select
    ) {

        return;

    }


    const current =
        select.value;


    select.innerHTML =
        `
        <option value="">
            ${escapeHtml(t("allWarehouses"))}
        </option>
        `;


    warehouses.forEach(
        warehouse => {

            select.insertAdjacentHTML(
                "beforeend",
                `
                <option value="${escapeHtml(warehouse.id)}">
                    ${escapeHtml(warehouse.name)}
                </option>
                `
            );

        }
    );


    if (
        [...select.options]
            .some(
                option =>
                    option.value ===
                    current
            )
    ) {

        select.value =
            current;

    }

}


function populateWarehouseFormSelect(
    id
) {

    const select =
        document.getElementById(
            id
        );


    if (
        !select
    ) {

        return;

    }


    const current =
        select.value;


    select.innerHTML =
        "";


    warehouses
        .filter(
            warehouse =>
                warehouse.active
        )
        .forEach(
            warehouse => {

                select.insertAdjacentHTML(
                    "beforeend",
                    `
                    <option value="${escapeHtml(warehouse.id)}">
                        ${escapeHtml(warehouse.name)}
                        —
                        ${escapeHtml(warehouse.code)}
                    </option>
                    `
                );

            }
        );


    if (
        [...select.options]
            .some(
                option =>
                    option.value ===
                    current
            )
    ) {

        select.value =
            current;

    }

}


function populateCategorySelect(
    id
) {

    const select =
        document.getElementById(
            id
        );


    select.innerHTML =
        "";


    CATEGORIES.forEach(
        category => {

            select.insertAdjacentHTML(
                "beforeend",
                `
                <option value="${escapeHtml(category.uz)}">
                    ${escapeHtml(
                        getCategoryLabel(
                            category.uz
                        )
                    )}
                </option>
                `
            );

        }
    );

}


function populateCategoryFilter(
    id
) {

    const select =
        document.getElementById(
            id
        );


    if (
        !select
    ) {

        return;

    }


    const current =
        select.value;


    select.innerHTML =
        `
        <option value="">
            ${escapeHtml(t("allCategories"))}
        </option>
        `;


    CATEGORIES.forEach(
        category => {

            select.insertAdjacentHTML(
                "beforeend",
                `
                <option value="${escapeHtml(category.uz)}">
                    ${escapeHtml(
                        getCategoryLabel(
                            category.uz
                        )
                    )}
                </option>
                `
            );

        }
    );


    select.value =
        current;

}


function populateSubcategories(
    categoryName,
    selectId
) {

    const category =
        findCategory(
            categoryName
        );


    const select =
        document.getElementById(
            selectId
        );


    select.innerHTML =
        "";


    if (
        !category
    ) {

        return;

    }


    category
        .subcategories
        .forEach(
            item => {

                select.insertAdjacentHTML(
                    "beforeend",
                    `
                    <option value="${escapeHtml(item)}">
                        ${escapeHtml(item)}
                    </option>
                    `
                );

            }
        );

}


function populateCounterpartySelects() {

    const importSelect =
        document.getElementById(
            "importCounterparty"
        );


    const currentImport =
        importSelect.value;


    importSelect.innerHTML =
        `
        <option value="">
            ${escapeHtml(t("supplier"))}
        </option>
        `;


    counterparties
        .filter(
            item =>
                item.active
                &&
                (
                    item.type ===
                    "supplier"
                    ||
                    item.type ===
                    "both"
                )
        )
        .forEach(
            item => {

                importSelect.insertAdjacentHTML(
                    "beforeend",
                    `
                    <option value="${escapeHtml(item.id)}">
                        ${escapeHtml(item.name)}
                    </option>
                    `
                );

            }
        );


    importSelect.value =
        currentImport;


    const saleBuyer =
        document.getElementById(
            "saleBuyer"
        );


    const currentBuyer =
        saleBuyer.value;


    saleBuyer.innerHTML =
        `
        <option value="">
            ${escapeHtml(t("retailCustomer"))}
        </option>
        `;


    counterparties
        .filter(
            item =>
                item.active
                &&
                (
                    item.type ===
                    "buyer"
                    ||
                    item.type ===
                    "both"
                )
        )
        .forEach(
            item => {

                saleBuyer.insertAdjacentHTML(
                    "beforeend",
                    `
                    <option value="${escapeHtml(item.id)}">
                        ${escapeHtml(item.name)}
                    </option>
                    `
                );

            }
        );


    saleBuyer.value =
        currentBuyer;

}


function populateSaleProductSelect() {

    const select =
        document.getElementById(
            "saleProduct"
        );


    const warehouseId =
        valueOf(
            "saleWarehouse"
        );


    const current =
        select.value;


    select.innerHTML =
        `
        <option value="">
            ${escapeHtml(t("product"))}
        </option>
        `;


    if (
        !warehouseId
    ) {

        return;

    }


    products
        .filter(
            product =>
                productStockInWarehouse(
                    product,
                    warehouseId
                )
                >
                0
        )
        .forEach(
            product => {

                const stock =
                    productStockInWarehouse(
                        product,
                        warehouseId
                    );


                select.insertAdjacentHTML(
                    "beforeend",
                    `
                    <option value="${escapeHtml(product.id)}">
                        ${escapeHtml(product.name)}
                        —
                        ${escapeHtml(product.sku)}
                        (${formatNumber(stock)})
                    </option>
                    `
                );

            }
        );


    if (
        [...select.options]
            .some(
                option =>
                    option.value ===
                    current
            )
    ) {

        select.value =
            current;

    }

}


/* =========================================================
   PREPARE MODALS
========================================================= */

function prepareWarehouseModal() {

    document
        .getElementById(
            "warehouseForm"
        )
        .reset();


    setValue(
        "warehouseArea",
        0
    );


    setValue(
        "warehouseCapacity",
        0
    );

}


function prepareProductModal() {

    document
        .getElementById(
            "productForm"
        )
        .reset();


    productPhotoData =
        "";


    renderPhotoPreview(
        "productPhotoPreview",
        ""
    );


    populateWarehouseFormSelect(
        "productWarehouse"
    );


    const category =
        CATEGORIES[0].uz;


    setValue(
        "productCategory",
        category
    );


    populateSubcategories(
        category,
        "productSubcategory"
    );


    setValue(
        "productSku",
        generateSku(
            category
        )
    );


    setValue(
        "productPurchasePrice",
        0
    );


    setValue(
        "productMarkup",
        20
    );


    setValue(
        "productSalePrice",
        0
    );


    setValue(
        "productOpeningStock",
        0
    );


    setValue(
        "productMinStock",
        settings.lowStock
        ||
        5
    );


    const suggested =
        suggestedWarehouseForCategory(
            category
        );


    setValue(
        "productWarehouse",
        suggested.id
    );

}


function prepareImportModal() {

    document
        .getElementById(
            "importForm"
        )
        .reset();


    importPhotoData =
        "";


    renderPhotoPreview(
        "importPhotoPreview",
        ""
    );


    populateWarehouseFormSelect(
        "importWarehouse"
    );


    setValue(
        "importDate",
        today()
    );


    const category =
        CATEGORIES[0].uz;


    setValue(
        "importCategory",
        category
    );


    populateSubcategories(
        category,
        "importSubcategory"
    );


    setValue(
        "importSku",
        generateSku(
            category
        )
    );


    setValue(
        "importQuantity",
        1
    );


    setValue(
        "importPurchasePrice",
        0
    );


    setValue(
        "importMarkup",
        20
    );


    setValue(
        "importSalePrice",
        0
    );


    setValue(
        "importMinStock",
        settings.lowStock
        ||
        5
    );


    const suggested =
        suggestedWarehouseForCategory(
            category
        );


    setValue(
        "importWarehouse",
        suggested.id
    );


    setText(
        "nextImportNumber",
        generateDocumentNumber(
            settings.importPrefix
            ||
            "IMP",
            imports
        )
    );


    updateImportSummary();

}


function prepareSaleModal() {

    document
        .getElementById(
            "saleForm"
        )
        .reset();


    populateWarehouseFormSelect(
        "saleWarehouse"
    );


    populateCounterpartySelects();


    const firstWarehouse =
        warehouses.find(
            warehouse =>
                warehouse.active
                &&
                warehouseTotalUnits(
                    warehouse.id
                )
                >
                0
        )
        ||
        warehouses.find(
            warehouse =>
                warehouse.active
        );


    if (
        firstWarehouse
    ) {

        setValue(
            "saleWarehouse",
            firstWarehouse.id
        );

    }


    populateSaleProductSelect();


    setValue(
        "saleQuantity",
        1
    );


    setValue(
        "saleDiscount",
        0
    );


    setText(
        "nextSaleNumber",
        generateDocumentNumber(
            settings.salePrefix
            ||
            "EXP",
            sales
        )
    );


    updateSaleProductInfo();

}


/* =========================================================
   PRICE CALCULATIONS
========================================================= */

function calculateProductSalePrice() {

    const purchase =
        numberValue(
            "productPurchasePrice"
        );


    const markup =
        numberValue(
            "productMarkup"
        );


    setValue(
        "productSalePrice",
        Math.round(
            purchase
            *
            (
                1 +
                markup / 100
            )
        )
    );

}


function calculateProductMarkup() {

    const purchase =
        numberValue(
            "productPurchasePrice"
        );


    const sale =
        numberValue(
            "productSalePrice"
        );


    if (
        purchase <=
        0
    ) {

        return;

    }


    setValue(
        "productMarkup",
        (
            (
                sale -
                purchase
            )
            /
            purchase
            *
            100
        )
        .toFixed(2)
    );

}


function calculateImportSalePrice() {

    const purchase =
        numberValue(
            "importPurchasePrice"
        );


    const markup =
        numberValue(
            "importMarkup"
        );


    setValue(
        "importSalePrice",
        Math.round(
            purchase
            *
            (
                1 +
                markup / 100
            )
        )
    );


    updateImportSummary();

}


function calculateImportMarkup() {

    const purchase =
        numberValue(
            "importPurchasePrice"
        );


    const sale =
        numberValue(
            "importSalePrice"
        );


    if (
        purchase >
        0
    ) {

        setValue(
            "importMarkup",
            (
                (
                    sale -
                    purchase
                )
                /
                purchase
                *
                100
            )
            .toFixed(2)
        );

    }


    updateImportSummary();

}


function updateImportSummary() {

    const quantity =
        numberValue(
            "importQuantity"
        );


    const purchase =
        numberValue(
            "importPurchasePrice"
        );


    const sale =
        numberValue(
            "importSalePrice"
        );


    const purchaseTotal =
        quantity *
        purchase;


    const retailTotal =
        quantity *
        sale;


    setText(
        "importSummaryQuantity",
        formatNumber(
            quantity
        )
    );


    setText(
        "importSummaryPurchase",
        money(
            purchaseTotal
        )
    );


    setText(
        "importSummaryRetail",
        money(
            retailTotal
        )
    );


    setText(
        "importSummaryProfit",
        money(
            retailTotal -
            purchaseTotal
        )
    );

}


/* =========================================================
   SALE CALC
========================================================= */

function selectedSaleProduct() {

    const id =
        valueOf(
            "saleProduct"
        );


    return products.find(
        product =>
            product.id ===
            id
    );

}


function updateSaleProductInfo() {

    const warehouseId =
        valueOf(
            "saleWarehouse"
        );


    const product =
        selectedSaleProduct();


    if (
        !warehouseId
        ||
        !product
    ) {

        setText(
            "saleStockInfo",
            "—"
        );


        setText(
            "salePurchaseInfo",
            "—"
        );


        setText(
            "salePriceInfo",
            "—"
        );


        setValue(
            "salePrice",
            ""
        );


        calculateSale();

        return;

    }


    const stock =
        productStockInWarehouse(
            product,
            warehouseId
        );


    setText(
        "saleStockInfo",
        `${formatNumber(stock)} ${product.unit}`
    );


    setText(
        "salePurchaseInfo",
        money(
            product.purchasePrice
        )
    );


    setText(
        "salePriceInfo",
        money(
            product.salePrice
        )
    );


    setValue(
        "salePrice",
        product.salePrice
    );


    document
        .getElementById(
            "saleQuantity"
        )
        .max =
            stock;


    calculateSale();

}


function calculateSale() {

    const product =
        selectedSaleProduct();


    const quantity =
        numberValue(
            "saleQuantity"
        );


    const price =
        numberValue(
            "salePrice"
        );


    const discount =
        Math.min(
            100,
            numberValue(
                "saleDiscount"
            )
        );


    const subtotal =
        quantity *
        price;


    const discountAmount =
        subtotal
        *
        discount
        /
        100;


    const total =
        subtotal -
        discountAmount;


    const cost =
        product
        ?
        product.purchasePrice
        *
        quantity
        :
        0;


    setText(
        "saleSubtotal",
        money(
            subtotal
        )
    );


    setText(
        "saleDiscountAmount",
        money(
            discountAmount
        )
    );


    setText(
        "saleGrandTotal",
        money(
            total
        )
    );


    setText(
        "saleProfitPreview",
        money(
            total -
            cost
        )
    );

}


/* =========================================================
   CREATE WAREHOUSE
========================================================= */

function createWarehouse(
    event
) {

    event.preventDefault();


    const code =
        valueOf(
            "warehouseCode"
        )
        .toUpperCase();


    if (
        warehouses.some(
            warehouse =>
                normalize(
                    warehouse.code
                )
                ===
                normalize(
                    code
                )
        )
    ) {

        showToast(
            t("error"),
            t("warehouseCodeExists"),
            "error"
        );

        return;

    }


    const warehouse = {

        id:
            generateId(
                "WH",
                warehouses
            ),

        code,

        name:
            valueOf(
                "warehouseName"
            ),

        type:
            valueOf(
                "warehouseType"
            ),

        manager:
            valueOf(
                "warehouseManager"
            ),

        phone:
            valueOf(
                "warehousePhone"
            ),

        address:
            valueOf(
                "warehouseAddress"
            ),

        area:
            numberValue(
                "warehouseArea"
            ),

        capacity:
            numberValue(
                "warehouseCapacity"
            ),

        temperature:
            valueOf(
                "warehouseTemperature"
            ),

        notes:
            valueOf(
                "warehouseNotes"
            ),

        active:
            true

    };


    warehouses.push(
        warehouse
    );


    save(
        STORAGE.warehouses,
        warehouses
    );


    closeModal(
        "warehouseModal"
    );


    populateDynamicSelects();

    renderAll();


    showToast(
        t("warehouseCreated"),
        warehouse.name
    );

}


/* =========================================================
   CREATE PRODUCT
========================================================= */

function createProduct(
    event
) {

    event.preventDefault();


    const category =
        valueOf(
            "productCategory"
        );


    const warehouseId =
        valueOf(
            "productWarehouse"
        );


    const openingStock =
        numberValue(
            "productOpeningStock"
        );


    const purchasePrice =
        numberValue(
            "productPurchasePrice"
        );


    const salePrice =
        numberValue(
            "productSalePrice"
        );


    const product = {

        id:
            generateId(
                "PRD",
                products
            ),

        sku:
            valueOf(
                "productSku"
            )
            ||
            generateSku(
                category
            ),

        name:
            valueOf(
                "productName"
            ),

        category,

        subcategory:
            valueOf(
                "productSubcategory"
            ),

        brand:
            valueOf(
                "productBrand"
            ),

        model:
            valueOf(
                "productModel"
            ),

        barcode:
            valueOf(
                "productBarcode"
            ),

        purchasePrice,

        salePrice,

        markup:
            purchasePrice > 0
            ?
            (
                (
                    salePrice -
                    purchasePrice
                )
                /
                purchasePrice
                *
                100
            )
            :
            0,

        stockByWarehouse: {
            [warehouseId]:
                openingStock
        },

        defaultWarehouseId:
            warehouseId,

        stock:
            openingStock,

        minStock:
            numberValue(
                "productMinStock"
            ),

        unit:
            valueOf(
                "productUnit"
            ),

        location:
            valueOf(
                "productLocation"
            ),

        photo:
            productPhotoData

    };


    products.unshift(
        product
    );


    save(
        STORAGE.products,
        products
    );


    closeModal(
        "productModal"
    );


    populateDynamicSelects();

    renderAll();


    showToast(
        t("productCreated"),
        `${product.name} • ${product.sku}`
    );

}


/* =========================================================
   CREATE IMPORT
========================================================= */

function createImport(
    event
) {

    event.preventDefault();


    const warehouseId =
        valueOf(
            "importWarehouse"
        );


    const warehouse =
        getWarehouse(
            warehouseId
        );


    const supplierId =
        valueOf(
            "importCounterparty"
        );


    const supplier =
        counterparties.find(
            item =>
                item.id ===
                supplierId
        );


    if (
        !warehouse
        ||
        !supplier
    ) {

        return;

    }


    const category =
        valueOf(
            "importCategory"
        );


    const productName =
        valueOf(
            "importProductName"
        );


    const quantity =
        numberValue(
            "importQuantity"
        );


    const purchasePrice =
        numberValue(
            "importPurchasePrice"
        );


    const salePrice =
        numberValue(
            "importSalePrice"
        );


    let product =
        products.find(
            item =>
                normalize(
                    item.name
                )
                ===
                normalize(
                    productName
                )
                &&
                normalizeCategory(
                    item.category
                )
                ===
                normalizeCategory(
                    category
                )
        );


    if (
        product
    ) {

        ensureStockObject(
            product
        );


        product.stockByWarehouse[
            warehouseId
        ] =
            Number(
                product.stockByWarehouse[
                    warehouseId
                ]
                ||
                0
            )
            +
            quantity;


        product.purchasePrice =
            purchasePrice;


        product.salePrice =
            salePrice;


        product.markup =
            purchasePrice > 0
            ?
            (
                (
                    salePrice -
                    purchasePrice
                )
                /
                purchasePrice
                *
                100
            )
            :
            0;


        if (
            importPhotoData
        ) {

            product.photo =
                importPhotoData;

        }


        syncLegacyStock(
            product
        );

    } else {

        product = {

            id:
                generateId(
                    "PRD",
                    products
                ),

            sku:
                valueOf(
                    "importSku"
                )
                ||
                generateSku(
                    category
                ),

            name:
                productName,

            category,

            subcategory:
                valueOf(
                    "importSubcategory"
                ),

            brand:
                valueOf(
                    "importBrand"
                ),

            model:
                "",

            barcode:
                "",

            purchasePrice,

            salePrice,

            markup:
                purchasePrice > 0
                ?
                (
                    (
                        salePrice -
                        purchasePrice
                    )
                    /
                    purchasePrice
                    *
                    100
                )
                :
                0,

            stockByWarehouse: {
                [warehouseId]:
                    quantity
            },

            defaultWarehouseId:
                warehouseId,

            stock:
                quantity,

            minStock:
                numberValue(
                    "importMinStock"
                ),

            unit:
                valueOf(
                    "importUnit"
                ),

            location:
                valueOf(
                    "importLocation"
                ),

            photo:
                importPhotoData

        };


        products.unshift(
            product
        );

    }


    const documentData = {

        id:
            generateDocumentNumber(
                settings.importPrefix
                ||
                "IMP",
                imports
            ),

        date:
            valueOf(
                "importDate"
            ),

        warehouseId,

        warehouseName:
            warehouse.name,

        counterpartyId:
            supplier.id,

        counterpartyName:
            supplier.name,

        supplierInvoice:
            valueOf(
                "supplierInvoice"
            ),

        productId:
            product.id,

        sku:
            product.sku,

        productName:
            product.name,

        category:
            product.category,

        quantity,

        purchasePrice,

        salePrice,

        totalPurchase:
            quantity *
            purchasePrice,

        totalRetail:
            quantity *
            salePrice,

        userName:
            currentUser.fullName
            ||
            currentUser.username,

        createdAt:
            new Date()
                .toISOString()

    };


    imports.unshift(
        documentData
    );


    save(
        STORAGE.products,
        products
    );


    save(
        STORAGE.imports,
        imports
    );


    closeModal(
        "importModal"
    );


    populateDynamicSelects();

    renderAll();


    showToast(
        t("importCreated"),
        `${documentData.id} • ${warehouse.name}`
    );

}


/* =========================================================
   CREATE SALE
========================================================= */

function createSale(
    event
) {

    event.preventDefault();


    const warehouseId =
        valueOf(
            "saleWarehouse"
        );


    const warehouse =
        getWarehouse(
            warehouseId
        );


    const product =
        selectedSaleProduct();


    if (
        !warehouse
        ||
        !product
    ) {

        return;

    }


    const availableStock =
        productStockInWarehouse(
            product,
            warehouseId
        );


    const quantity =
        numberValue(
            "saleQuantity"
        );


    if (
        quantity >
        availableStock
    ) {

        showToast(
            t("error"),
            t("insufficientStock"),
            "error"
        );

        return;

    }


    const price =
        numberValue(
            "salePrice"
        );


    const discount =
        Math.min(
            100,
            numberValue(
                "saleDiscount"
            )
        );


    const subtotal =
        quantity *
        price;


    const total =
        subtotal
        *
        (
            1 -
            discount / 100
        );


    const cost =
        quantity
        *
        product.purchasePrice;


    const buyerId =
        valueOf(
            "saleBuyer"
        );


    const buyer =
        counterparties.find(
            item =>
                item.id ===
                buyerId
        );


    ensureStockObject(
        product
    );


    product.stockByWarehouse[
        warehouseId
    ] =
        Number(
            product.stockByWarehouse[
                warehouseId
            ]
            ||
            0
        )
        -
        quantity;


    syncLegacyStock(
        product
    );


    const documentData = {

        id:
            generateDocumentNumber(
                settings.salePrefix
                ||
                "EXP",
                sales
            ),

        date:
            today(),

        warehouseId,

        warehouseName:
            warehouse.name,

        productId:
            product.id,

        sku:
            product.sku,

        productName:
            product.name,

        category:
            product.category,

        quantity,

        purchasePrice:
            product.purchasePrice,

        salePrice:
            price,

        discount,

        total:
            Math.round(
                total
            ),

        cost:
            Math.round(
                cost
            ),

        profit:
            Math.round(
                total -
                cost
            ),

        buyerName:
            buyer
            ?
            buyer.name
            :
            t(
                "retailCustomer"
            ),

        userName:
            currentUser.fullName
            ||
            currentUser.username

    };


    sales.unshift(
        documentData
    );


    save(
        STORAGE.products,
        products
    );


    save(
        STORAGE.sales,
        sales
    );


    closeModal(
        "saleModal"
    );


    populateDynamicSelects();

    renderAll();


    showToast(
        t("saleCreated"),
        `${documentData.id} • ${warehouse.name}`
    );

}


/* =========================================================
   CREATE COUNTERPARTY
========================================================= */

function createCounterparty(
    event
) {

    event.preventDefault();


    const item = {

        id:
            generateId(
                "CTR",
                counterparties
            ),

        name:
            valueOf(
                "counterpartyName"
            ),

        type:
            valueOf(
                "counterpartyFormType"
            ),

        inn:
            valueOf(
                "counterpartyInn"
            ),

        phone:
            valueOf(
                "counterpartyPhone"
            ),

        email:
            valueOf(
                "counterpartyEmail"
            ),

        contact:
            valueOf(
                "counterpartyContact"
            ),

        address:
            valueOf(
                "counterpartyAddress"
            ),

        bank:
            valueOf(
                "counterpartyBank"
            ),

        active:
            true

    };


    counterparties.unshift(
        item
    );


    save(
        STORAGE.counterparties,
        counterparties
    );


    event.target.reset();


    closeModal(
        "counterpartyModal"
    );


    populateCounterpartySelects();

    renderCounterparties();


    showToast(
        t("counterpartyCreated"),
        item.name
    );

}


/* =========================================================
   CREATE USER
========================================================= */

async function createUser(
    event
) {

    event.preventDefault();


    const fullName =
        valueOf(
            "newUserFullName"
        );


    const username =
        valueOf(
            "newUserLogin"
        );


    const role =
        valueOf(
            "newUserRole"
        );


    const password =
        valueOf(
            "newUserPassword"
        );


    const confirmation =
        valueOf(
            "newUserConfirm"
        );


    if (
        password !==
        confirmation
    ) {

        showToast(
            t("error"),
            t("passwordsMismatch"),
            "error"
        );

        return;

    }


    const users =
        load(
            STORAGE.users,
            []
        );


    if (
        users.some(
            user =>
                normalize(
                    user.username
                )
                ===
                normalize(
                    username
                )
        )
    ) {

        showToast(
            t("error"),
            t("loginExists"),
            "error"
        );

        return;

    }


    const roles = {
        admin: "Administrator",
        warehouse_manager: "Warehouse Manager",
        storekeeper: "Storekeeper",
        cashier: "Cashier",
        accountant: "Accountant",
        viewer: "Viewer"
    };


    const newUser = {

        id:
            generateId(
                "USR",
                users
            ),

        fullName,

        username,

        passwordHash:
            await sha256(
                password
            ),

        role,

        roleName:
            roles[role]
            ||
            role,

        active:
            true,

        permissions:
            [],

        createdAt:
            new Date()
                .toISOString(),

        lastLogin:
            null

    };


    users.push(
        newUser
    );


    save(
        STORAGE.users,
        users
    );


    event.target.reset();


    closeModal(
        "userModal"
    );


    renderUsers();


    showToast(
        t("userCreated"),
        newUser.fullName
    );

}


/* =========================================================
   SETTINGS
========================================================= */

function saveSettings(
    event
) {

    event.preventDefault();


    settings = {

        companyName:
            valueOf(
                "settingsCompany"
            ),

        inn:
            valueOf(
                "settingsInn"
            ),

        phone:
            valueOf(
                "settingsPhone"
            ),

        address:
            valueOf(
                "settingsAddress"
            ),

        currency:
            valueOf(
                "settingsCurrency"
            ),

        importPrefix:
            valueOf(
                "settingsImportPrefix"
            )
            .toUpperCase(),

        salePrefix:
            valueOf(
                "settingsSalePrefix"
            )
            .toUpperCase(),

        lowStock:
            numberValue(
                "settingsLowStock"
            )

    };


    save(
        STORAGE.settings,
        settings
    );


    renderSettings();

    renderSidebar();


    showToast(
        t("settingsSaved"),
        settings.companyName
    );

}


/* =========================================================
   RENDER ALL
========================================================= */

function renderAll() {

    renderDashboard();

    renderWarehouses();

    renderStock();

    renderImports();

    renderSales();

    renderProducts();

    renderCounterparties();

    renderReports();

    renderUsers();

    renderSettings();

    renderSidebar();

}


/* =========================================================
   DASHBOARD
========================================================= */

function renderDashboard() {

    const totalStock =
        sum(
            products,
            product =>
                productTotalStock(
                    product
                )
        );


    const purchaseValue =
        sum(
            products,
            product =>
                productTotalStock(
                    product
                )
                *
                product.purchasePrice
        );


    const todaySales =
        sales.filter(
            item =>
                item.date ===
                today()
        );


    const revenue =
        sum(
            todaySales,
            item =>
                item.total
        );


    setText(
        "dashboardWarehouses",
        warehouses.filter(
            warehouse =>
                warehouse.active
        ).length
    );


    setText(
        "dashboardStock",
        formatNumber(
            totalStock
        )
    );


    setText(
        "dashboardPurchase",
        money(
            purchaseValue
        )
    );


    setText(
        "dashboardRevenue",
        money(
            revenue
        )
    );


    setText(
        "dashboardDate",
        longDate(
            new Date()
        )
    );


    renderSalesChart();

    renderWarehouseDistribution();

    renderRecentOperations();

    renderLowStock();

}


/* =========================================================
   DASHBOARD CHART
========================================================= */

function renderSalesChart() {

    const days =
        [];


    for (
        let index = 6;
        index >= 0;
        index--
    ) {

        const date =
            dateDaysAgo(
                index
            );


        const iso =
            isoDate(
                date
            );


        days.push({

            date,

            amount:
                sum(
                    sales.filter(
                        sale =>
                            sale.date ===
                            iso
                    ),
                    sale =>
                        sale.total
                )

        });

    }


    const max =
        Math.max(
            ...days.map(
                day =>
                    day.amount
            ),
            1
        );


    document
        .getElementById(
            "salesChart"
        )
        .innerHTML =
            days.map(
                day => {

                    const height =
                        Math.max(
                            4,
                            day.amount
                            /
                            max
                            *
                            76
                        );


                    return `
                    <div class="chart-column">

                        <span class="chart-number">
                            ${compactMoney(day.amount)}
                        </span>

                        <div
                            class="chart-bar"
                            style="height:${height}%"
                        ></div>

                        <span class="chart-day">
                            ${shortDay(day.date)}
                        </span>

                    </div>
                    `;

                }
            )
            .join("");

}


/* =========================================================
   WAREHOUSE DISTRIBUTION
========================================================= */

function renderWarehouseDistribution() {

    const data =
        warehouses
            .map(
                warehouse => ({

                    warehouse,

                    quantity:
                        warehouseTotalUnits(
                            warehouse.id
                        )

                })
            )
            .filter(
                item =>
                    item.quantity >
                    0
            )
            .sort(
                (
                    a,
                    b
                ) =>
                    b.quantity -
                    a.quantity
            );


    const max =
        Math.max(
            ...data.map(
                item =>
                    item.quantity
            ),
            1
        );


    document
        .getElementById(
            "dashboardWarehouseProgress"
        )
        .innerHTML =
            data.length
            ?
            data.map(
                item => `

                <div class="progress-row">

                    <span>
                        ${escapeHtml(item.warehouse.name)}
                    </span>

                    <div class="progress-track">

                        <span
                            style="width:${item.quantity / max * 100}%"
                        ></span>

                    </div>

                    <span>
                        ${formatNumber(item.quantity)}
                    </span>

                </div>

                `
            )
            .join("")
            :
            `<div class="empty-state">${escapeHtml(t("noData"))}</div>`;

}


/* =========================================================
   RECENT OPERATIONS
========================================================= */

function renderRecentOperations() {

    const operations = [

        ...imports.map(
            item => ({

                id:
                    item.id,

                type:
                    "import",

                warehouseName:
                    item.warehouseName,

                amount:
                    item.totalPurchase,

                date:
                    item.date

            })
        ),

        ...sales.map(
            item => ({

                id:
                    item.id,

                type:
                    "sale",

                warehouseName:
                    item.warehouseName,

                amount:
                    item.total,

                date:
                    item.date

            })
        )

    ]
    .sort(
        (
            a,
            b
        ) =>
            new Date(b.date)
            -
            new Date(a.date)
    )
    .slice(
        0,
        6
    );


    const body =
        document.getElementById(
            "recentOperations"
        );


    if (
        !operations.length
    ) {

        body.innerHTML =
            emptyRow(
                5
            );

        return;

    }


    body.innerHTML =
        operations.map(
            item => `

            <tr>

                <td>
                    <span class="document-number">
                        ${escapeHtml(item.id)}
                    </span>
                </td>

                <td>
                    ${
                        item.type ===
                        "import"
                        ?
                        escapeHtml(
                            t(
                                "importOperation"
                            )
                        )
                        :
                        escapeHtml(
                            t(
                                "saleOperation"
                            )
                        )
                    }
                </td>

                <td>
                    ${escapeHtml(item.warehouseName || "—")}
                </td>

                <td class="table-main">
                    ${money(item.amount)}
                </td>

                <td>
                    ${formatDate(item.date)}
                </td>

            </tr>

            `
        )
        .join("");

}


/* =========================================================
   LOW STOCK
========================================================= */

function renderLowStock() {

    const rows =
        getAllStockRows()
            .filter(
                row =>
                    row.quantity >
                    0
                    &&
                    row.quantity
                    <=
                    Number(
                        row.product.minStock
                        ||
                        settings.lowStock
                    )
            )
            .sort(
                (
                    a,
                    b
                ) =>
                    a.quantity -
                    b.quantity
            )
            .slice(
                0,
                6
            );


    setText(
        "lowStockCount",
        rows.length
    );


    const container =
        document.getElementById(
            "lowStockList"
        );


    if (
        !rows.length
    ) {

        container.innerHTML =
            `
            <div class="empty-state">
                ${escapeHtml(t("noLowStock"))}
            </div>
            `;

        return;

    }


    container.innerHTML =
        rows.map(
            row => `

            <div class="low-stock-item">

                ${productImage(row.product)}

                <div class="low-stock-copy">

                    <strong>
                        ${escapeHtml(row.product.name)}
                    </strong>

                    <span>
                        ${escapeHtml(row.warehouse.name)}
                        •
                        ${escapeHtml(row.product.sku)}
                    </span>

                </div>

                <div class="low-stock-value">
                    ${formatNumber(row.quantity)}
                </div>

            </div>

            `
        )
        .join("");

}


/* =========================================================
   WAREHOUSES
========================================================= */

function renderWarehouses() {

    const search =
        normalize(
            valueOf(
                "warehousesSearch"
            )
        );


    const type =
        valueOf(
            "warehouseTypeFilter"
        );


    let filtered =
        [...warehouses];


    if (
        search
    ) {

        filtered =
            filtered.filter(
                warehouse =>
                    [
                        warehouse.name,
                        warehouse.code,
                        warehouse.manager,
                        warehouse.address,
                        warehouse.phone
                    ]
                    .some(
                        value =>
                            normalize(value)
                            .includes(search)
                    )
            );

    }


    if (
        type
    ) {

        filtered =
            filtered.filter(
                warehouse =>
                    warehouse.type ===
                    type
            );

    }


    renderWarehouseCards(
        filtered
    );


    const body =
        document.getElementById(
            "warehousesTable"
        );


    if (
        !filtered.length
    ) {

        body.innerHTML =
            emptyRow(
                10
            );

        return;

    }


    body.innerHTML =
        filtered.map(
            warehouse => {

                const metrics =
                    warehouseMetrics(
                        warehouse.id
                    );


                return `

                <tr>

                    <td>

                        <div class="product-cell">

                            <div class="product-placeholder">
                                ${escapeHtml(warehouse.code.slice(0,2))}
                            </div>

                            <div class="product-cell-copy">

                                <strong>
                                    ${escapeHtml(warehouse.name)}
                                </strong>

                                <span>
                                    ${escapeHtml(warehouse.code)}
                                </span>

                            </div>

                        </div>

                    </td>

                    <td>
                        <span class="type-badge">
                            ${escapeHtml(
                                warehouseTypeLabel(
                                    warehouse.type
                                )
                            )}
                        </span>
                    </td>

                    <td>
                        ${escapeHtml(warehouse.manager || "—")}
                    </td>

                    <td>
                        ${escapeHtml(warehouse.address || "—")}
                    </td>

                    <td>
                        ${
                            warehouse.capacity
                            ?
                            formatNumber(warehouse.capacity)
                            :
                            "—"
                        }
                    </td>

                    <td>
                        ${formatNumber(metrics.positions)}
                    </td>

                    <td class="table-main">
                        ${formatNumber(metrics.units)}
                    </td>

                    <td>
                        ${money(metrics.purchaseValue)}
                    </td>

                    <td>
                        <span class="status-badge ${
                            warehouse.active
                            ?
                            "status-success"
                            :
                            "status-danger"
                        }">
                            ${
                                warehouse.active
                                ?
                                escapeHtml(t("active"))
                                :
                                escapeHtml(t("inactive"))
                            }
                        </span>
                    </td>

                    <td>

                        <div class="row-actions">

                            <button
                                class="icon-button delete"
                                onclick="requestDeleteWarehouse('${warehouse.id}')"
                            >
                                <svg>
                                    <use href="#i-trash"></use>
                                </svg>
                            </button>

                        </div>

                    </td>

                </tr>

                `;

            }
        )
        .join("");

}


function renderWarehouseCards(
    list
) {

    const colors = [
        "#7156e5",
        "#13a899",
        "#ed8c36",
        "#397be6",
        "#1ba66d"
    ];


    document
        .getElementById(
            "warehouseCards"
        )
        .innerHTML =
            list.map(
                (
                    warehouse,
                    index
                ) => {

                    const metrics =
                        warehouseMetrics(
                            warehouse.id
                        );


                    return `

                    <article
                        class="warehouse-card"
                        style="--warehouse-accent:${colors[index % colors.length]}"
                    >

                        <div class="warehouse-card-header">

                            <div class="warehouse-card-icon">
                                <svg>
                                    <use href="#i-warehouse"></use>
                                </svg>
                            </div>

                            <span class="warehouse-code">
                                ${escapeHtml(warehouse.code)}
                            </span>

                        </div>

                        <h3>
                            ${escapeHtml(warehouse.name)}
                        </h3>

                        <p>
                            ${escapeHtml(warehouse.address || "—")}
                        </p>

                        <div class="warehouse-card-metrics">

                            <div>
                                <span>${escapeHtml(t("positions"))}</span>
                                <strong>${formatNumber(metrics.positions)}</strong>
                            </div>

                            <div>
                                <span>${escapeHtml(t("quantity"))}</span>
                                <strong>${formatNumber(metrics.units)}</strong>
                            </div>

                        </div>

                    </article>

                    `;

                }
            )
            .join("");

}


/* =========================================================
   STOCK
========================================================= */

function getFilteredStockRows() {

    const search =
        normalize(
            valueOf(
                "stockSearch"
            )
        );


    const warehouseId =
        valueOf(
            "stockWarehouseFilter"
        );


    const category =
        valueOf(
            "stockCategoryFilter"
        );


    const status =
        valueOf(
            "stockStatusFilter"
        );


    let rows =
        getAllStockRows();


    if (
        warehouseId
    ) {

        rows =
            rows.filter(
                row =>
                    row.warehouse.id ===
                    warehouseId
            );

    }


    if (
        category
    ) {

        rows =
            rows.filter(
                row =>
                    normalizeCategory(
                        row.product.category
                    )
                    ===
                    normalizeCategory(
                        category
                    )
            );

    }


    if (
        search
    ) {

        rows =
            rows.filter(
                row =>
                    [
                        row.product.name,
                        row.product.sku,
                        row.product.brand,
                        row.warehouse.name,
                        row.warehouse.code
                    ]
                    .some(
                        value =>
                            normalize(value)
                            .includes(search)
                    )
            );

    }


    if (
        status ===
        "available"
    ) {

        rows =
            rows.filter(
                row =>
                    row.quantity >
                    Number(
                        row.product.minStock
                        ||
                        settings.lowStock
                    )
            );

    }


    if (
        status ===
        "low"
    ) {

        rows =
            rows.filter(
                row =>
                    row.quantity >
                    0
                    &&
                    row.quantity
                    <=
                    Number(
                        row.product.minStock
                        ||
                        settings.lowStock
                    )
            );

    }


    if (
        status ===
        "zero"
    ) {

        rows =
            rows.filter(
                row =>
                    row.quantity <=
                    0
            );

    }


    return rows;

}


function renderStock() {

    const rows =
        getFilteredStockRows();


    const body =
        document.getElementById(
            "stockTable"
        );


    if (
        !rows.length
    ) {

        body.innerHTML =
            emptyRow(
                9
            );

    } else {

        body.innerHTML =
            rows.map(
                row => `

                <tr>

                    <td>
                        ${productCell(row.product)}
                    </td>

                    <td>
                        ${escapeHtml(row.product.sku)}
                    </td>

                    <td>
                        <span class="type-badge">
                            ${escapeHtml(row.warehouse.name)}
                        </span>
                    </td>

                    <td>
                        ${escapeHtml(
                            getCategoryLabel(
                                row.product.category
                            )
                        )}
                    </td>

                    <td>
                        ${money(row.product.purchasePrice)}
                    </td>

                    <td>
                        ${money(row.product.salePrice)}
                    </td>

                    <td class="table-main">
                        ${formatNumber(row.quantity)}
                        ${escapeHtml(row.product.unit)}
                    </td>

                    <td>
                        ${money(
                            row.quantity
                            *
                            row.product.purchasePrice
                        )}
                    </td>

                    <td>
                        ${stockStatus(
                            row.product,
                            row.quantity
                        )}
                    </td>

                </tr>

                `
            )
            .join("");

    }


    setText(
        "stockPositions",
        rows.length
    );


    setText(
        "stockUnits",
        formatNumber(
            sum(
                rows,
                row =>
                    row.quantity
            )
        )
    );


    setText(
        "stockPurchaseValue",
        money(
            sum(
                rows,
                row =>
                    row.quantity
                    *
                    row.product.purchasePrice
            )
        )
    );


    setText(
        "stockRetailValue",
        money(
            sum(
                rows,
                row =>
                    row.quantity
                    *
                    row.product.salePrice
            )
        )
    );

}


/* =========================================================
   IMPORTS
========================================================= */

function filteredImports() {

    const search =
        normalize(
            valueOf(
                "importsSearch"
            )
        );


    const warehouseId =
        valueOf(
            "importsWarehouseFilter"
        );


    let filtered =
        filterByPeriod(
            imports,
            importReportFilter
        );


    if (
        warehouseId
    ) {

        filtered =
            filtered.filter(
                item =>
                    item.warehouseId ===
                    warehouseId
            );

    }


    if (
        search
    ) {

        filtered =
            filtered.filter(
                item =>
                    [
                        item.id,
                        item.counterpartyName,
                        item.productName,
                        item.sku,
                        item.warehouseName
                    ]
                    .some(
                        value =>
                            normalize(value)
                            .includes(search)
                    )
            );

    }


    return filtered;

}


function renderImports() {

    const filtered =
        filteredImports();


    const body =
        document.getElementById(
            "importsTable"
        );


    if (
        !filtered.length
    ) {

        body.innerHTML =
            emptyRow(
                10
            );

    } else {

        body.innerHTML =
            filtered.map(
                item => `

                <tr>

                    <td>
                        <span class="document-number">
                            ${escapeHtml(item.id)}
                        </span>
                    </td>

                    <td>
                        ${formatDate(item.date)}
                    </td>

                    <td>
                        <span class="type-badge">
                            ${escapeHtml(item.warehouseName || warehouseName(item.warehouseId))}
                        </span>
                    </td>

                    <td>
                        ${escapeHtml(item.counterpartyName)}
                    </td>

                    <td>
                        ${escapeHtml(item.productName)}
                    </td>

                    <td>
                        ${formatNumber(item.quantity)}
                    </td>

                    <td>
                        ${money(item.purchasePrice)}
                    </td>

                    <td class="table-main">
                        ${money(item.totalPurchase)}
                    </td>

                    <td>
                        ${escapeHtml(item.userName || "—")}
                    </td>

                    <td>

                        <div class="row-actions">

                            <button
                                class="icon-button"
                                onclick="printImportDocument('${item.id}')"
                            >
                                <svg>
                                    <use href="#i-print"></use>
                                </svg>
                            </button>

                        </div>

                    </td>

                </tr>

                `
            )
            .join("");

    }


    setText(
        "importsCount",
        filtered.length
    );


    setText(
        "importsUnits",
        formatNumber(
            sum(
                filtered,
                item =>
                    item.quantity
            )
        )
    );


    setText(
        "importsPurchaseTotal",
        money(
            sum(
                filtered,
                item =>
                    item.totalPurchase
            )
        )
    );


    setText(
        "importsRetailTotal",
        money(
            sum(
                filtered,
                item =>
                    item.totalRetail
            )
        )
    );

}


/* =========================================================
   SALES
========================================================= */

function filteredSales() {

    const search =
        normalize(
            valueOf(
                "salesSearch"
            )
        );


    const warehouseId =
        valueOf(
            "salesWarehouseFilter"
        );


    let filtered =
        filterByPeriod(
            sales,
            salesReportFilter
        );


    if (
        warehouseId
    ) {

        filtered =
            filtered.filter(
                item =>
                    item.warehouseId ===
                    warehouseId
            );

    }


    if (
        search
    ) {

        filtered =
            filtered.filter(
                item =>
                    [
                        item.id,
                        item.productName,
                        item.sku,
                        item.buyerName,
                        item.warehouseName
                    ]
                    .some(
                        value =>
                            normalize(value)
                            .includes(search)
                    )
            );

    }


    return filtered;

}


function renderSales() {

    const filtered =
        filteredSales();


    const body =
        document.getElementById(
            "salesTable"
        );


    if (
        !filtered.length
    ) {

        body.innerHTML =
            emptyRow(
                10
            );

    } else {

        body.innerHTML =
            filtered.map(
                item => `

                <tr>

                    <td>
                        <span class="document-number">
                            ${escapeHtml(item.id)}
                        </span>
                    </td>

                    <td>
                        ${formatDate(item.date)}
                    </td>

                    <td>
                        <span class="type-badge">
                            ${escapeHtml(item.warehouseName || warehouseName(item.warehouseId))}
                        </span>
                    </td>

                    <td>
                        ${escapeHtml(item.productName)}
                    </td>

                    <td>
                        ${formatNumber(item.quantity)}
                    </td>

                    <td>
                        ${money(item.purchasePrice)}
                    </td>

                    <td>
                        ${money(item.salePrice)}
                    </td>

                    <td class="table-main">
                        ${money(item.total)}
                    </td>

                    <td>
                        <span style="color:var(--green);font-weight:700">
                            ${money(item.profit)}
                        </span>
                    </td>

                    <td>

                        <div class="row-actions">

                            <button
                                class="icon-button"
                                onclick="printSaleDocument('${item.id}')"
                            >
                                <svg>
                                    <use href="#i-print"></use>
                                </svg>
                            </button>

                        </div>

                    </td>

                </tr>

                `
            )
            .join("");

    }


    setText(
        "salesCount",
        filtered.length
    );


    setText(
        "salesUnits",
        formatNumber(
            sum(
                filtered,
                item =>
                    item.quantity
            )
        )
    );


    setText(
        "salesRevenue",
        money(
            sum(
                filtered,
                item =>
                    item.total
            )
        )
    );


    setText(
        "salesProfit",
        money(
            sum(
                filtered,
                item =>
                    item.profit
            )
        )
    );

}


/* =========================================================
   PRODUCTS
========================================================= */

function renderProducts() {

    const search =
        normalize(
            valueOf(
                "productsSearch"
            )
        );


    const warehouseId =
        valueOf(
            "productsWarehouseFilter"
        );


    const category =
        valueOf(
            "productsCategoryFilter"
        );


    let filtered =
        [...products];


    if (
        warehouseId
    ) {

        filtered =
            filtered.filter(
                product =>
                    productStockInWarehouse(
                        product,
                        warehouseId
                    )
                    >
                    0
            );

    }


    if (
        category
    ) {

        filtered =
            filtered.filter(
                product =>
                    normalizeCategory(
                        product.category
                    )
                    ===
                    normalizeCategory(
                        category
                    )
            );

    }


    if (
        search
    ) {

        filtered =
            filtered.filter(
                product =>
                    [
                        product.name,
                        product.sku,
                        product.brand,
                        product.model
                    ]
                    .some(
                        value =>
                            normalize(value)
                            .includes(search)
                    )
            );

    }


    const body =
        document.getElementById(
            "productsTable"
        );


    if (
        !filtered.length
    ) {

        body.innerHTML =
            emptyRow(
                10
            );

        return;

    }


    body.innerHTML =
        filtered.map(
            product => {

                const displayedStock =
                    warehouseId
                    ?
                    productStockInWarehouse(
                        product,
                        warehouseId
                    )
                    :
                    productTotalStock(
                        product
                    );


                return `

                <tr>

                    <td>
                        ${productCell(product)}
                    </td>

                    <td>
                        ${escapeHtml(product.sku)}
                    </td>

                    <td>
                        ${escapeHtml(
                            getCategoryLabel(
                                product.category
                            )
                        )}
                    </td>

                    <td>
                        ${escapeHtml(product.brand || "—")}
                    </td>

                    <td>
                        ${productWarehouseTags(product)}
                    </td>

                    <td>
                        ${money(product.purchasePrice)}
                    </td>

                    <td class="table-main">
                        ${money(product.salePrice)}
                    </td>

                    <td>
                        ${Number(product.markup || 0).toFixed(2)}%
                    </td>

                    <td>
                        ${formatNumber(displayedStock)}
                        ${escapeHtml(product.unit)}
                    </td>

                    <td>

                        <div class="row-actions">

                            <button
                                class="icon-button delete"
                                onclick="requestDeleteProduct('${product.id}')"
                            >
                                <svg>
                                    <use href="#i-trash"></use>
                                </svg>
                            </button>

                        </div>

                    </td>

                </tr>

                `;

            }
        )
        .join("");

}


/* =========================================================
   COUNTERPARTIES
========================================================= */

function renderCounterparties() {

    const search =
        normalize(
            valueOf(
                "counterpartiesSearch"
            )
        );


    const type =
        valueOf(
            "counterpartyTypeFilter"
        );


    let filtered =
        [...counterparties];


    if (
        search
    ) {

        filtered =
            filtered.filter(
                item =>
                    [
                        item.name,
                        item.inn,
                        item.phone,
                        item.contact,
                        item.address
                    ]
                    .some(
                        value =>
                            normalize(value)
                            .includes(search)
                    )
            );

    }


    if (
        type
    ) {

        filtered =
            filtered.filter(
                item =>
                    item.type ===
                    type
            );

    }


    const body =
        document.getElementById(
            "counterpartiesTable"
        );


    if (
        !filtered.length
    ) {

        body.innerHTML =
            emptyRow(
                8
            );

    } else {

        body.innerHTML =
            filtered.map(
                item => `

                <tr>

                    <td>

                        <div class="product-cell">

                            <div class="product-placeholder">
                                ${getInitials(item.name)}
                            </div>

                            <div class="product-cell-copy">

                                <strong>
                                    ${escapeHtml(item.name)}
                                </strong>

                                <span>
                                    ${escapeHtml(item.email || "—")}
                                </span>

                            </div>

                        </div>

                    </td>

                    <td>
                        <span class="type-badge">
                            ${escapeHtml(
                                counterpartyTypeLabel(
                                    item.type
                                )
                            )}
                        </span>
                    </td>

                    <td>
                        ${escapeHtml(item.inn || "—")}
                    </td>

                    <td>
                        ${escapeHtml(item.phone || "—")}
                    </td>

                    <td>
                        ${escapeHtml(item.contact || "—")}
                    </td>

                    <td>
                        ${escapeHtml(item.address || "—")}
                    </td>

                    <td>
                        <span class="status-badge status-success">
                            ${escapeHtml(t("active"))}
                        </span>
                    </td>

                    <td>

                        <div class="row-actions">

                            <button
                                class="icon-button delete"
                                onclick="requestDeleteCounterparty('${item.id}')"
                            >
                                <svg>
                                    <use href="#i-trash"></use>
                                </svg>
                            </button>

                        </div>

                    </td>

                </tr>

                `
            )
            .join("");

    }


    setText(
        "counterpartyCount",
        counterparties.length
    );


    setText(
        "supplierCount",
        counterparties.filter(
            item =>
                item.type ===
                "supplier"
                ||
                item.type ===
                "both"
        ).length
    );


    setText(
        "buyerCount",
        counterparties.filter(
            item =>
                item.type ===
                "buyer"
                ||
                item.type ===
                "both"
        ).length
    );

}


/* =========================================================
   REPORTS
========================================================= */

function getFullReportData() {

    const from =
        valueOf(
            "reportFrom"
        );


    const to =
        valueOf(
            "reportTo"
        );


    const warehouseId =
        valueOf(
            "reportWarehouseFilter"
        );


    return {

        from,
        to,
        warehouseId,

        imports:
            imports.filter(
                item =>
                    (
                        !from
                        ||
                        item.date >=
                        from
                    )
                    &&
                    (
                        !to
                        ||
                        item.date <=
                        to
                    )
                    &&
                    (
                        !warehouseId
                        ||
                        item.warehouseId ===
                        warehouseId
                    )
            ),

        sales:
            sales.filter(
                item =>
                    (
                        !from
                        ||
                        item.date >=
                        from
                    )
                    &&
                    (
                        !to
                        ||
                        item.date <=
                        to
                    )
                    &&
                    (
                        !warehouseId
                        ||
                        item.warehouseId ===
                        warehouseId
                    )
            )

    };

}


function renderReports() {

    const report =
        getFullReportData();


    const importTotal =
        sum(
            report.imports,
            item =>
                item.totalPurchase
        );


    const revenue =
        sum(
            report.sales,
            item =>
                item.total
        );


    const cost =
        sum(
            report.sales,
            item =>
                item.cost
        );


    const profit =
        sum(
            report.sales,
            item =>
                item.profit
        );


    setText(
        "reportImportTotal",
        money(
            importTotal
        )
    );


    setText(
        "reportRevenue",
        money(
            revenue
        )
    );


    setText(
        "reportCost",
        money(
            cost
        )
    );


    setText(
        "reportProfit",
        money(
            profit
        )
    );


    const stockRows =
        report.warehouseId
        ?
        getAllStockRows()
            .filter(
                row =>
                    row.warehouse.id ===
                    report.warehouseId
            )
        :
        getAllStockRows();


    const units =
        sum(
            stockRows,
            row =>
                row.quantity
        );


    const purchaseValue =
        sum(
            stockRows,
            row =>
                row.quantity
                *
                row.product.purchasePrice
        );


    const retailValue =
        sum(
            stockRows,
            row =>
                row.quantity
                *
                row.product.salePrice
        );


    setText(
        "reportPositions",
        stockRows.filter(
            row =>
                row.quantity >
                0
        ).length
    );


    setText(
        "reportUnits",
        formatNumber(
            units
        )
    );


    setText(
        "reportStockPurchase",
        money(
            purchaseValue
        )
    );


    setText(
        "reportStockRetail",
        money(
            retailValue
        )
    );


    setText(
        "reportPotentialProfit",
        money(
            retailValue -
            purchaseValue
        )
    );


    setText(
        "reportWarehouseName",
        report.warehouseId
        ?
        warehouseName(
            report.warehouseId
        )
        :
        t(
            "allWarehouses"
        )
    );


    renderReportCategoryBars(
        report.sales
    );

}


/* =========================================================
   REPORT BARS
========================================================= */

function renderReportCategoryBars(
    reportSales
) {

    const data =
        CATEGORIES
            .map(
                category => ({

                    category:
                        category.uz,

                    amount:
                        sum(
                            reportSales.filter(
                                item =>
                                    normalizeCategory(
                                        item.category
                                    )
                                    ===
                                    category.uz
                            ),
                            item =>
                                item.total
                        )

                })
            )
            .filter(
                item =>
                    item.amount >
                    0
            )
            .sort(
                (
                    a,
                    b
                ) =>
                    b.amount -
                    a.amount
            )
            .slice(
                0,
                7
            );


    const container =
        document.getElementById(
            "reportCategoryBars"
        );


    if (
        !data.length
    ) {

        container.innerHTML =
            `
            <div class="empty-state">
                ${escapeHtml(t("noData"))}
            </div>
            `;

        return;

    }


    const max =
        Math.max(
            ...data.map(
                item =>
                    item.amount
            )
        );


    container.innerHTML =
        data.map(
            item => `

            <div class="report-bar-row">

                <span>
                    ${escapeHtml(
                        getCategoryLabel(
                            item.category
                        )
                    )}
                </span>

                <div class="report-bar-track">

                    <span
                        style="width:${item.amount / max * 100}%"
                    ></span>

                </div>

                <strong>
                    ${compactMoney(item.amount)}
                </strong>

            </div>

            `
        )
        .join("");

}


/* =========================================================
   USERS
========================================================= */

function renderUsers() {

    const users =
        load(
            STORAGE.users,
            []
        );


    const search =
        normalize(
            valueOf(
                "usersSearch"
            )
        );


    const filtered =
        users.filter(
            user =>
                !search
                ||
                [
                    user.fullName,
                    user.username,
                    user.roleName
                ]
                .some(
                    value =>
                        normalize(value)
                        .includes(search)
                )
        );


    const body =
        document.getElementById(
            "usersTable"
        );


    if (
        !filtered.length
    ) {

        body.innerHTML =
            emptyRow(
                7
            );

        return;

    }


    body.innerHTML =
        filtered.map(
            user => `

            <tr>

                <td>

                    <div class="product-cell">

                        <div class="product-placeholder">
                            ${getInitials(user.fullName)}
                        </div>

                        <div class="product-cell-copy">

                            <strong>
                                ${escapeHtml(user.fullName)}
                            </strong>

                            <span>
                                ${escapeHtml(user.id)}
                            </span>

                        </div>

                    </div>

                </td>

                <td>
                    ${escapeHtml(user.username)}
                </td>

                <td>
                    <span class="type-badge">
                        ${escapeHtml(user.roleName || user.role)}
                    </span>
                </td>

                <td>
                    <span class="status-badge status-success">
                        ${escapeHtml(t("active"))}
                    </span>
                </td>

                <td>
                    ${
                        user.lastLogin
                        ?
                        formatDateTime(
                            user.lastLogin
                        )
                        :
                        "—"
                    }
                </td>

                <td>
                    ${
                        user.createdAt
                        ?
                        formatDateTime(
                            user.createdAt
                        )
                        :
                        "—"
                    }
                </td>

                <td>

                    ${
                        user.role !==
                        "superadmin"
                        ?
                        `
                        <div class="row-actions">

                            <button
                                class="icon-button delete"
                                onclick="requestDeleteUser('${user.id}')"
                            >
                                <svg>
                                    <use href="#i-trash"></use>
                                </svg>
                            </button>

                        </div>
                        `
                        :
                        ""
                    }

                </td>

            </tr>

            `
        )
        .join("");

}


/* =========================================================
   SETTINGS
========================================================= */

function renderSettings() {

    setValue(
        "settingsCompany",
        settings.companyName
    );


    setValue(
        "settingsInn",
        settings.inn
    );


    setValue(
        "settingsPhone",
        settings.phone
    );


    setValue(
        "settingsAddress",
        settings.address
    );


    setValue(
        "settingsCurrency",
        settings.currency
    );


    setValue(
        "settingsImportPrefix",
        settings.importPrefix
    );


    setValue(
        "settingsSalePrefix",
        settings.salePrefix
    );


    setValue(
        "settingsLowStock",
        settings.lowStock
    );

}


function renderSidebar() {

    setText(
        "sidebarCompany",
        settings.companyName
    );


    setText(
        "sidebarWarehouseCount",
        warehouses.filter(
            warehouse =>
                warehouse.active
        ).length
    );

}


/* =========================================================
   STOCK HELPERS
========================================================= */

function ensureStockObject(
    product
) {

    if (
        !product.stockByWarehouse
        ||
        typeof product.stockByWarehouse
        !==
        "object"
    ) {

        product.stockByWarehouse =
            {};

    }

}


function productStockInWarehouse(
    product,
    warehouseId
) {

    ensureStockObject(
        product
    );


    return Number(
        product.stockByWarehouse[
            warehouseId
        ]
        ||
        0
    );

}


function productTotalStock(
    product
) {

    ensureStockObject(
        product
    );


    return Object
        .values(
            product.stockByWarehouse
        )
        .reduce(
            (
                total,
                quantity
            ) =>
                total
                +
                Number(
                    quantity
                    ||
                    0
                ),
            0
        );

}


function syncLegacyStock(
    product
) {

    product.stock =
        productTotalStock(
            product
        );

}


function getAllStockRows() {

    const rows =
        [];


    products.forEach(
        product => {

            ensureStockObject(
                product
            );


            warehouses.forEach(
                warehouse => {

                    const hasKey =
                        Object.prototype
                            .hasOwnProperty
                            .call(
                                product.stockByWarehouse,
                                warehouse.id
                            );


                    const quantity =
                        productStockInWarehouse(
                            product,
                            warehouse.id
                        );


                    if (
                        hasKey
                        ||
                        product.defaultWarehouseId ===
                        warehouse.id
                    ) {

                        rows.push({
                            product,
                            warehouse,
                            quantity
                        });

                    }

                }
            );

        }
    );


    return rows;

}


function warehouseMetrics(
    warehouseId
) {

    const rows =
        getAllStockRows()
            .filter(
                row =>
                    row.warehouse.id ===
                    warehouseId
            );


    const activeRows =
        rows.filter(
            row =>
                row.quantity >
                0
        );


    return {

        positions:
            activeRows.length,

        units:
            sum(
                activeRows,
                row =>
                    row.quantity
            ),

        purchaseValue:
            sum(
                activeRows,
                row =>
                    row.quantity
                    *
                    row.product.purchasePrice
            ),

        retailValue:
            sum(
                activeRows,
                row =>
                    row.quantity
                    *
                    row.product.salePrice
            )

    };

}


function warehouseTotalUnits(
    warehouseId
) {

    return warehouseMetrics(
        warehouseId
    ).units;

}


/* =========================================================
   WAREHOUSE HELPERS
========================================================= */

function getWarehouse(
    warehouseId
) {

    return warehouses.find(
        warehouse =>
            warehouse.id ===
            warehouseId
    );

}


function warehouseName(
    warehouseId
) {

    return getWarehouse(
        warehouseId
    )?.name
    ||
    "—";

}


function suggestedWarehouseForCategory(
    categoryName
) {

    const category =
        findCategory(
            categoryName
        );


    const type =
        category?.warehouseType
        ||
        "universal";


    return (
        warehouses.find(
            warehouse =>
                warehouse.active
                &&
                warehouse.type ===
                type
        )
        ||
        warehouses.find(
            warehouse =>
                warehouse.active
                &&
                warehouse.type ===
                "universal"
        )
        ||
        warehouses.find(
            warehouse =>
                warehouse.active
        )
        ||
        warehouses[0]
    );

}


function warehouseTypeLabel(
    type
) {

    const keys = {
        universal:
            "warehouseUniversal",

        electronics:
            "warehouseElectronics",

        food:
            "warehouseFood",

        clothing:
            "warehouseClothing",

        household:
            "warehouseHousehold",

        other:
            "warehouseOther"
    };


    return t(
        keys[type]
        ||
        "warehouseOther"
    );

}


/* =========================================================
   PRODUCT UI
========================================================= */

function productCell(
    product
) {

    return `

    <div class="product-cell">

        ${productImage(product)}

        <div class="product-cell-copy">

            <strong>
                ${escapeHtml(product.name)}
            </strong>

            <span>
                ${escapeHtml(
                    product.brand
                    ||
                    product.subcategory
                    ||
                    ""
                )}
            </span>

        </div>

    </div>

    `;

}


function productImage(
    product
) {

    if (
        product.photo
    ) {

        return `
        <img
            class="product-image"
            src="${product.photo}"
            alt=""
        >
        `;

    }


    return `
    <div class="product-placeholder">
        ${getInitials(product.name)}
    </div>
    `;

}


function productWarehouseTags(
    product
) {

    ensureStockObject(
        product
    );


    const ids =
        Object.entries(
            product.stockByWarehouse
        )
        .filter(
            (
                [
                    ,
                    quantity
                ]
            ) =>
                Number(quantity)
                >
                0
        )
        .map(
            (
                [
                    id
                ]
            ) =>
                id
        );


    if (
        !ids.length
    ) {

        return "—";

    }


    return `
    <div class="warehouse-tags">

        ${
            ids.map(
                id => {

                    const warehouse =
                        getWarehouse(
                            id
                        );


                    if (
                        !warehouse
                    ) {

                        return "";

                    }


                    return `
                    <span class="warehouse-tag">
                        ${escapeHtml(warehouse.code)}
                        :
                        ${formatNumber(
                            productStockInWarehouse(
                                product,
                                id
                            )
                        )}
                    </span>
                    `;

                }
            )
            .join("")
        }

    </div>
    `;

}


function stockStatus(
    product,
    quantity
) {

    if (
        quantity <=
        0
    ) {

        return `
        <span class="status-badge status-danger">
            ${escapeHtml(t("outOfStock"))}
        </span>
        `;

    }


    if (
        quantity <=
        Number(
            product.minStock
            ||
            settings.lowStock
        )
    ) {

        return `
        <span class="status-badge status-warning">
            ${escapeHtml(t("lowStock"))}
        </span>
        `;

    }


    return `
    <span class="status-badge status-success">
        ${escapeHtml(t("available"))}
    </span>
    `;

}


/* =========================================================
   CATEGORY HELPERS
========================================================= */

function findCategory(
    value
) {

    const normalized =
        normalize(
            value
        );


    return CATEGORIES.find(
        category =>
            [
                category.uz,
                category.ru,
                category.en
            ]
            .some(
                label =>
                    normalize(label)
                    ===
                    normalized
            )
    );

}


function normalizeCategory(
    value
) {

    return findCategory(
        value
    )?.uz
    ||
    value;

}


function getCategoryLabel(
    value
) {

    const category =
        findCategory(
            value
        );


    if (
        !category
    ) {

        return value;

    }


    return category[
        currentLanguage
    ]
    ||
    category.uz;

}


/* =========================================================
   COUNTERPARTY LABEL
========================================================= */

function counterpartyTypeLabel(
    type
) {

    if (
        type ===
        "supplier"
    ) {

        return t(
            "supplier"
        );

    }


    if (
        type ===
        "buyer"
    ) {

        return t(
            "buyer"
        );

    }


    return t(
        "both"
    );

}


/* =========================================================
   FILTER PERIOD
========================================================= */

function filterByPeriod(
    collection,
    filter
) {

    return collection.filter(
        item => {

            if (
                filter.from
                &&
                item.date <
                filter.from
            ) {

                return false;

            }


            if (
                filter.to
                &&
                item.date >
                filter.to
            ) {

                return false;

            }


            return true;

        }
    );

}


/* =========================================================
   DELETE WAREHOUSE
========================================================= */

window.requestDeleteWarehouse =
    function(
        id
    ) {

        const warehouse =
            getWarehouse(
                id
            );


        if (
            !warehouse
        ) {

            return;

        }


        const units =
            warehouseTotalUnits(
                id
            );


        if (
            units >
            0
        ) {

            showToast(
                t("error"),
                t("warehouseHasStock"),
                "error"
            );

            return;

        }


        const hasDocuments =
            imports.some(
                item =>
                    item.warehouseId ===
                    id
            )
            ||
            sales.some(
                item =>
                    item.warehouseId ===
                    id
            );


        if (
            hasDocuments
        ) {

            showToast(
                t("error"),
                t("warehouseHasDocuments"),
                "error"
            );

            return;

        }


        openConfirm(
            t("deleteWarehouse"),
            warehouse.name,
            () => {

                warehouses =
                    warehouses.filter(
                        item =>
                            item.id !==
                            id
                    );


                save(
                    STORAGE.warehouses,
                    warehouses
                );


                populateDynamicSelects();

                renderAll();

            }
        );

    };


/* =========================================================
   DELETE PRODUCT
========================================================= */

window.requestDeleteProduct =
    function(
        id
    ) {

        const product =
            products.find(
                item =>
                    item.id ===
                    id
            );


        if (
            !product
        ) {

            return;

        }


        openConfirm(
            t("deleteProduct"),
            product.name,
            () => {

                products =
                    products.filter(
                        item =>
                            item.id !==
                            id
                    );


                save(
                    STORAGE.products,
                    products
                );


                populateSaleProductSelect();

                renderAll();

            }
        );

    };


/* =========================================================
   DELETE COUNTERPARTY
========================================================= */

window.requestDeleteCounterparty =
    function(
        id
    ) {

        const item =
            counterparties.find(
                counterparty =>
                    counterparty.id ===
                    id
            );


        if (
            !item
        ) {

            return;

        }


        openConfirm(
            t("deleteCounterparty"),
            item.name,
            () => {

                counterparties =
                    counterparties.filter(
                        counterparty =>
                            counterparty.id !==
                            id
                    );


                save(
                    STORAGE.counterparties,
                    counterparties
                );


                populateCounterpartySelects();

                renderAll();

            }
        );

    };


/* =========================================================
   DELETE USER
========================================================= */

window.requestDeleteUser =
    function(
        id
    ) {

        let users =
            load(
                STORAGE.users,
                []
            );


        const user =
            users.find(
                item =>
                    item.id ===
                    id
            );


        if (
            !user
        ) {

            return;

        }


        openConfirm(
            t("deleteUser"),
            user.fullName,
            () => {

                users =
                    users.filter(
                        item =>
                            item.id !==
                            id
                    );


                save(
                    STORAGE.users,
                    users
                );


                renderUsers();

            }
        );

    };


function openConfirm(
    title,
    message,
    callback
) {

    setText(
        "confirmTitle",
        title
    );


    setText(
        "confirmText",
        message
    );


    confirmCallback =
        callback;


    openModal(
        "confirmModal"
    );

}


/* =========================================================
   PRINT INDIVIDUAL IMPORT
========================================================= */

window.printImportDocument =
    function(
        id
    ) {

        const item =
            imports.find(
                documentData =>
                    documentData.id ===
                    id
            );


        if (
            !item
        ) {

            return;

        }


        printHtml(
            createPrintTemplate(
                `

                <h1>
                    ${escapeHtml(t("imports"))}
                    —
                    ${escapeHtml(item.id)}
                </h1>


                <div class="report-period">

                    <b>${escapeHtml(t("date"))}:</b>
                    ${formatDate(item.date)}

                    <br>

                    <b>${escapeHtml(t("warehouse"))}:</b>
                    ${escapeHtml(item.warehouseName)}

                    <br>

                    <b>${escapeHtml(t("counterparty"))}:</b>
                    ${escapeHtml(item.counterpartyName)}

                    <br>

                    <b>${escapeHtml(t("supplierInvoice"))}:</b>
                    ${escapeHtml(item.supplierInvoice || "—")}

                </div>


                <table>

                    <thead>
                    <tr>
                        <th>${escapeHtml(t("sku"))}</th>
                        <th>${escapeHtml(t("product"))}</th>
                        <th>${escapeHtml(t("quantity"))}</th>
                        <th>${escapeHtml(t("purchasePrice"))}</th>
                        <th>${escapeHtml(t("salePrice"))}</th>
                        <th>${escapeHtml(t("amount"))}</th>
                    </tr>
                    </thead>

                    <tbody>

                    <tr>
                        <td>${escapeHtml(item.sku)}</td>
                        <td>${escapeHtml(item.productName)}</td>
                        <td>${formatNumber(item.quantity)}</td>
                        <td>${money(item.purchasePrice)}</td>
                        <td>${money(item.salePrice)}</td>
                        <td>${money(item.totalPurchase)}</td>
                    </tr>

                    </tbody>

                </table>

                `
            )
        );

    };


/* =========================================================
   PRINT SALE DOCUMENT
========================================================= */

window.printSaleDocument =
    function(
        id
    ) {

        const item =
            sales.find(
                documentData =>
                    documentData.id ===
                    id
            );


        if (
            !item
        ) {

            return;

        }


        printHtml(
            createPrintTemplate(
                `

                <h1>
                    ${escapeHtml(t("sales"))}
                    —
                    ${escapeHtml(item.id)}
                </h1>


                <div class="report-period">

                    <b>${escapeHtml(t("date"))}:</b>
                    ${formatDate(item.date)}

                    <br>

                    <b>${escapeHtml(t("warehouse"))}:</b>
                    ${escapeHtml(item.warehouseName)}

                    <br>

                    <b>${escapeHtml(t("buyer"))}:</b>
                    ${escapeHtml(item.buyerName)}

                </div>


                <table>

                    <thead>
                    <tr>
                        <th>${escapeHtml(t("sku"))}</th>
                        <th>${escapeHtml(t("product"))}</th>
                        <th>${escapeHtml(t("quantity"))}</th>
                        <th>${escapeHtml(t("purchasePrice"))}</th>
                        <th>${escapeHtml(t("salePrice"))}</th>
                        <th>${escapeHtml(t("amount"))}</th>
                    </tr>
                    </thead>

                    <tbody>

                    <tr>
                        <td>${escapeHtml(item.sku)}</td>
                        <td>${escapeHtml(item.productName)}</td>
                        <td>${formatNumber(item.quantity)}</td>
                        <td>${money(item.purchasePrice)}</td>
                        <td>${money(item.salePrice)}</td>
                        <td>${money(item.total)}</td>
                    </tr>

                    </tbody>

                </table>

                `
            )
        );

    };


/* =========================================================
   PRINT IMPORT REPORT
========================================================= */

function printImportsReport() {

    const items =
        filteredImports();


    const warehouseId =
        valueOf(
            "importsWarehouseFilter"
        );


    const rows =
        items.map(
            item => `

            <tr>
                <td>${escapeHtml(item.id)}</td>
                <td>${formatDate(item.date)}</td>
                <td>${escapeHtml(item.warehouseName)}</td>
                <td>${escapeHtml(item.counterpartyName)}</td>
                <td>${escapeHtml(item.sku)}</td>
                <td>${escapeHtml(item.productName)}</td>
                <td>${formatNumber(item.quantity)}</td>
                <td>${money(item.purchasePrice)}</td>
                <td>${money(item.totalPurchase)}</td>
            </tr>

            `
        )
        .join("");


    printHtml(
        createPrintTemplate(
            `

            <h1>
                ${escapeHtml(t("importReportTitle"))}
            </h1>


            ${printReportMeta(
                reportPeriodText(
                    importReportFilter
                ),
                warehouseId
            )}


            ${printMetrics([
                {
                    label: t("documents"),
                    value: formatNumber(items.length)
                },
                {
                    label: t("quantity"),
                    value: formatNumber(
                        sum(
                            items,
                            item => item.quantity
                        )
                    )
                },
                {
                    label: t("purchaseTotal"),
                    value: money(
                        sum(
                            items,
                            item => item.totalPurchase
                        )
                    )
                },
                {
                    label: t("potentialRetail"),
                    value: money(
                        sum(
                            items,
                            item => item.totalRetail
                        )
                    )
                }
            ])}


            <table>

                <thead>
                <tr>
                    <th>${escapeHtml(t("document"))}</th>
                    <th>${escapeHtml(t("date"))}</th>
                    <th>${escapeHtml(t("warehouse"))}</th>
                    <th>${escapeHtml(t("counterparty"))}</th>
                    <th>${escapeHtml(t("sku"))}</th>
                    <th>${escapeHtml(t("product"))}</th>
                    <th>${escapeHtml(t("quantity"))}</th>
                    <th>${escapeHtml(t("purchasePrice"))}</th>
                    <th>${escapeHtml(t("amount"))}</th>
                </tr>
                </thead>

                <tbody>
                    ${
                        rows
                        ||
                        `<tr><td colspan="9">${escapeHtml(t("noData"))}</td></tr>`
                    }
                </tbody>

            </table>

            `
        )
    );

}


/* =========================================================
   PRINT SALES REPORT
========================================================= */

function printSalesReport() {

    const items =
        filteredSales();


    const warehouseId =
        valueOf(
            "salesWarehouseFilter"
        );


    const rows =
        items.map(
            item => `

            <tr>
                <td>${escapeHtml(item.id)}</td>
                <td>${formatDate(item.date)}</td>
                <td>${escapeHtml(item.warehouseName)}</td>
                <td>${escapeHtml(item.sku)}</td>
                <td>${escapeHtml(item.productName)}</td>
                <td>${formatNumber(item.quantity)}</td>
                <td>${money(item.purchasePrice)}</td>
                <td>${money(item.salePrice)}</td>
                <td>${money(item.total)}</td>
                <td>${money(item.profit)}</td>
            </tr>

            `
        )
        .join("");


    printHtml(
        createPrintTemplate(
            `

            <h1>
                ${escapeHtml(t("salesReportTitle"))}
            </h1>


            ${printReportMeta(
                reportPeriodText(
                    salesReportFilter
                ),
                warehouseId
            )}


            ${printMetrics([
                {
                    label: t("salesCount"),
                    value: formatNumber(items.length)
                },
                {
                    label: t("soldUnits"),
                    value: formatNumber(
                        sum(
                            items,
                            item => item.quantity
                        )
                    )
                },
                {
                    label: t("revenue"),
                    value: money(
                        sum(
                            items,
                            item => item.total
                        )
                    )
                },
                {
                    label: t("profit"),
                    value: money(
                        sum(
                            items,
                            item => item.profit
                        )
                    )
                }
            ])}


            <table>

                <thead>
                <tr>
                    <th>${escapeHtml(t("document"))}</th>
                    <th>${escapeHtml(t("date"))}</th>
                    <th>${escapeHtml(t("warehouse"))}</th>
                    <th>${escapeHtml(t("sku"))}</th>
                    <th>${escapeHtml(t("product"))}</th>
                    <th>${escapeHtml(t("quantity"))}</th>
                    <th>${escapeHtml(t("cost"))}</th>
                    <th>${escapeHtml(t("salePrice"))}</th>
                    <th>${escapeHtml(t("revenue"))}</th>
                    <th>${escapeHtml(t("profit"))}</th>
                </tr>
                </thead>

                <tbody>
                    ${
                        rows
                        ||
                        `<tr><td colspan="10">${escapeHtml(t("noData"))}</td></tr>`
                    }
                </tbody>

            </table>

            `
        )
    );

}


/* =========================================================
   PRINT STOCK
========================================================= */

function printStockReport() {

    const rows =
        getFilteredStockRows();


    const warehouseId =
        valueOf(
            "stockWarehouseFilter"
        );


    const htmlRows =
        rows.map(
            row => `

            <tr>
                <td>${escapeHtml(row.product.sku)}</td>
                <td>${escapeHtml(row.product.name)}</td>
                <td>${escapeHtml(row.warehouse.name)}</td>
                <td>${escapeHtml(getCategoryLabel(row.product.category))}</td>
                <td>${formatNumber(row.quantity)} ${escapeHtml(row.product.unit)}</td>
                <td>${money(row.product.purchasePrice)}</td>
                <td>${money(row.product.salePrice)}</td>
                <td>${money(row.quantity * row.product.purchasePrice)}</td>
            </tr>

            `
        )
        .join("");


    printHtml(
        createPrintTemplate(
            `

            <h1>
                ${escapeHtml(t("stockReportTitle"))}
            </h1>


            ${printReportMeta(
                t("periodAll"),
                warehouseId
            )}


            ${printMetrics([
                {
                    label: t("positions"),
                    value: formatNumber(rows.length)
                },
                {
                    label: t("quantity"),
                    value: formatNumber(
                        sum(
                            rows,
                            row => row.quantity
                        )
                    )
                },
                {
                    label: t("purchaseValue"),
                    value: money(
                        sum(
                            rows,
                            row =>
                                row.quantity *
                                row.product.purchasePrice
                        )
                    )
                },
                {
                    label: t("retailValue"),
                    value: money(
                        sum(
                            rows,
                            row =>
                                row.quantity *
                                row.product.salePrice
                        )
                    )
                }
            ])}


            <table>

                <thead>
                <tr>
                    <th>${escapeHtml(t("sku"))}</th>
                    <th>${escapeHtml(t("product"))}</th>
                    <th>${escapeHtml(t("warehouse"))}</th>
                    <th>${escapeHtml(t("category"))}</th>
                    <th>${escapeHtml(t("quantity"))}</th>
                    <th>${escapeHtml(t("purchasePrice"))}</th>
                    <th>${escapeHtml(t("salePrice"))}</th>
                    <th>${escapeHtml(t("stockAmount"))}</th>
                </tr>
                </thead>

                <tbody>
                    ${htmlRows}
                </tbody>

            </table>

            `
        )
    );

}


/* =========================================================
   PRINT FULL REPORT
========================================================= */

function printFullReport() {

    const report =
        getFullReportData();


    const stockRows =
        report.warehouseId
        ?
        getAllStockRows()
            .filter(
                row =>
                    row.warehouse.id ===
                    report.warehouseId
            )
        :
        getAllStockRows();


    const importRows =
        report.imports.map(
            item => `

            <tr>
                <td>${escapeHtml(item.id)}</td>
                <td>${formatDate(item.date)}</td>
                <td>${escapeHtml(item.warehouseName)}</td>
                <td>${escapeHtml(item.counterpartyName)}</td>
                <td>${escapeHtml(item.productName)}</td>
                <td>${formatNumber(item.quantity)}</td>
                <td>${money(item.totalPurchase)}</td>
            </tr>

            `
        )
        .join("");


    const salesRows =
        report.sales.map(
            item => `

            <tr>
                <td>${escapeHtml(item.id)}</td>
                <td>${formatDate(item.date)}</td>
                <td>${escapeHtml(item.warehouseName)}</td>
                <td>${escapeHtml(item.productName)}</td>
                <td>${formatNumber(item.quantity)}</td>
                <td>${money(item.total)}</td>
                <td>${money(item.profit)}</td>
            </tr>

            `
        )
        .join("");


    const stockHtml =
        stockRows.map(
            row => `

            <tr>
                <td>${escapeHtml(row.product.sku)}</td>
                <td>${escapeHtml(row.product.name)}</td>
                <td>${escapeHtml(row.warehouse.name)}</td>
                <td>${escapeHtml(getCategoryLabel(row.product.category))}</td>
                <td>${formatNumber(row.quantity)}</td>
                <td>${money(row.product.purchasePrice)}</td>
                <td>${money(row.quantity * row.product.purchasePrice)}</td>
            </tr>

            `
        )
        .join("");


    const period =
        report.from
        ||
        report.to
        ?
        `${report.from ? formatDate(report.from) : "—"} — ${report.to ? formatDate(report.to) : "—"}`
        :
        t(
            "periodAll"
        );


    printHtml(
        createPrintTemplate(
            `

            <h1>
                ${escapeHtml(t("reportTitle"))}
            </h1>


            ${printReportMeta(
                period,
                report.warehouseId
            )}


            ${printMetrics([
                {
                    label: t("purchaseTotal"),
                    value: money(
                        sum(
                            report.imports,
                            item => item.totalPurchase
                        )
                    )
                },
                {
                    label: t("revenue"),
                    value: money(
                        sum(
                            report.sales,
                            item => item.total
                        )
                    )
                },
                {
                    label: t("costOfSales"),
                    value: money(
                        sum(
                            report.sales,
                            item => item.cost
                        )
                    )
                },
                {
                    label: t("profit"),
                    value: money(
                        sum(
                            report.sales,
                            item => item.profit
                        )
                    )
                },
                {
                    label: t("purchaseValue"),
                    value: money(
                        sum(
                            stockRows,
                            row =>
                                row.quantity *
                                row.product.purchasePrice
                        )
                    )
                }
            ])}


            <h2>
                ${escapeHtml(t("importList"))}
            </h2>


            <table>

                <thead>
                <tr>
                    <th>${escapeHtml(t("document"))}</th>
                    <th>${escapeHtml(t("date"))}</th>
                    <th>${escapeHtml(t("warehouse"))}</th>
                    <th>${escapeHtml(t("counterparty"))}</th>
                    <th>${escapeHtml(t("product"))}</th>
                    <th>${escapeHtml(t("quantity"))}</th>
                    <th>${escapeHtml(t("amount"))}</th>
                </tr>
                </thead>

                <tbody>
                    ${
                        importRows
                        ||
                        `<tr><td colspan="7">${escapeHtml(t("noData"))}</td></tr>`
                    }
                </tbody>

            </table>


            <h2>
                ${escapeHtml(t("salesList"))}
            </h2>


            <table>

                <thead>
                <tr>
                    <th>${escapeHtml(t("document"))}</th>
                    <th>${escapeHtml(t("date"))}</th>
                    <th>${escapeHtml(t("warehouse"))}</th>
                    <th>${escapeHtml(t("product"))}</th>
                    <th>${escapeHtml(t("quantity"))}</th>
                    <th>${escapeHtml(t("revenue"))}</th>
                    <th>${escapeHtml(t("profit"))}</th>
                </tr>
                </thead>

                <tbody>
                    ${
                        salesRows
                        ||
                        `<tr><td colspan="7">${escapeHtml(t("noData"))}</td></tr>`
                    }
                </tbody>

            </table>


            <h2>
                ${escapeHtml(t("stockList"))}
            </h2>


            <table>

                <thead>
                <tr>
                    <th>${escapeHtml(t("sku"))}</th>
                    <th>${escapeHtml(t("product"))}</th>
                    <th>${escapeHtml(t("warehouse"))}</th>
                    <th>${escapeHtml(t("category"))}</th>
                    <th>${escapeHtml(t("quantity"))}</th>
                    <th>${escapeHtml(t("purchasePrice"))}</th>
                    <th>${escapeHtml(t("stockAmount"))}</th>
                </tr>
                </thead>

                <tbody>
                    ${stockHtml}
                </tbody>

            </table>

            `
        )
    );

}


/* =========================================================
   PRINT HELPERS
========================================================= */

function printReportMeta(
    period,
    warehouseId
) {

    return `
    <div class="report-period">

        <b>${escapeHtml(t("reportingPeriod"))}:</b>
        ${escapeHtml(period)}

        <br>

        <b>${escapeHtml(t("reportWarehouse"))}:</b>
        ${
            warehouseId
            ?
            escapeHtml(
                warehouseName(
                    warehouseId
                )
            )
            :
            escapeHtml(
                t(
                    "allWarehouses"
                )
            )
        }

        <br>

        <b>${escapeHtml(t("reportCreated"))}:</b>
        ${formatDateTime(new Date().toISOString())}

    </div>
    `;

}


function printMetrics(
    metrics
) {

    return `
    <div class="print-kpis">

        ${
            metrics.map(
                metric => `

                <div>

                    <span>
                        ${escapeHtml(metric.label)}
                    </span>

                    <strong>
                        ${escapeHtml(metric.value)}
                    </strong>

                </div>

                `
            )
            .join("")
        }

    </div>
    `;

}


function createPrintTemplate(
    content
) {

    return `
    <!DOCTYPE html>

    <html lang="${currentLanguage}">

    <head>

        <meta charset="UTF-8">

        <title>
            ${escapeHtml(settings.companyName)}
        </title>

        <style>

            @page {
                size: A4 landscape;
                margin: 12mm;
            }

            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;

                font-family:
                    Arial,
                    sans-serif;

                color:
                    #171717;

                font-size: 9px;
            }

            .company-header {
                margin-bottom: 18px;
                padding-bottom: 12px;

                display: flex;
                justify-content: space-between;
                align-items: flex-end;

                border-bottom:
                    2px solid #3a315f;
            }

            .company-header h3 {
                margin: 0;

                color:
                    #3a315f;

                font-size: 17px;
            }

            .company-header p {
                margin:
                    4px 0 0;

                color:
                    #777;

                font-size: 8px;
            }

            h1 {
                margin:
                    0 0 14px;

                font-size: 17px;
            }

            h2 {
                margin:
                    22px 0 8px;

                font-size: 12px;
            }

            .report-period {
                margin-bottom: 14px;

                padding:
                    9px 10px;

                border:
                    1px solid #ddd;

                background:
                    #fafafa;

                line-height: 1.7;
            }

            .print-kpis {
                margin-bottom: 16px;

                display: grid;

                grid-template-columns:
                    repeat(5,minmax(0,1fr));

                gap: 6px;
            }

            .print-kpis div {
                padding: 8px;

                border:
                    1px solid #dadada;

                border-radius: 4px;
            }

            .print-kpis span {
                display: block;

                color: #777;

                font-size: 7px;
            }

            .print-kpis strong {
                display: block;

                margin-top: 5px;

                font-size: 9px;
            }

            table {
                width: 100%;

                margin-bottom: 16px;

                border-collapse: collapse;
            }

            th,
            td {
                padding:
                    5px 6px;

                border:
                    1px solid #d5d5d5;

                text-align: left;

                vertical-align: top;
            }

            th {
                color:
                    #3a315f;

                background:
                    #f2f0f7;

                font-size: 7px;
            }

            td {
                font-size: 7.5px;
            }

            tr {
                page-break-inside: avoid;
            }

        </style>

    </head>


    <body>

        <div class="company-header">

            <div>

                <h3>
                    ${escapeHtml(settings.companyName)}
                </h3>

                <p>
                    ${
                        escapeHtml(
                            [
                                settings.inn,
                                settings.phone,
                                settings.address
                            ]
                            .filter(Boolean)
                            .join(" • ")
                        )
                    }
                </p>

            </div>

            <div>
                ${formatDateTime(new Date().toISOString())}
            </div>

        </div>

        ${content}

    </body>

    </html>
    `;

}


function printHtml(
    html
) {

    const printWindow =
        window.open(
            "",
            "_blank",
            "width=1200,height=850"
        );


    if (
        !printWindow
    ) {

        return;

    }


    printWindow.document.open();

    printWindow.document.write(
        html
    );

    printWindow.document.close();


    printWindow.onload =
        () => {

            printWindow.focus();

            printWindow.print();

        };

}


/* =========================================================
   REPORT DATE
========================================================= */

function setupReportDates() {

    const end =
        new Date();


    const start =
        new Date();


    start.setDate(
        start.getDate() -
        30
    );


    setValue(
        "reportFrom",
        isoDate(
            start
        )
    );


    setValue(
        "reportTo",
        isoDate(
            end
        )
    );

}


function reportPeriodText(
    filter
) {

    if (
        !filter.from
        &&
        !filter.to
    ) {

        return t(
            "periodAll"
        );

    }


    if (
        filter.from
        &&
        filter.to
        &&
        filter.from ===
        filter.to
    ) {

        return formatDate(
            filter.from
        );

    }


    return (
        `${filter.from ? formatDate(filter.from) : "—"} — ${filter.to ? formatDate(filter.to) : "—"}`
    );

}


/* =========================================================
   SKU
========================================================= */

function generateSku(
    categoryName
) {

    const category =
        findCategory(
            categoryName
        );


    const prefix =
        category?.prefix
        ||
        "PR";


    const numbers =
        products
            .filter(
                product =>
                    String(
                        product.sku
                    )
                    .startsWith(
                        `${prefix}-`
                    )
            )
            .map(
                product =>
                    parseInt(
                        String(
                            product.sku
                        )
                        .split("-")
                        .pop(),
                        10
                    )
            )
            .filter(
                Number.isFinite
            );


    const next =
        numbers.length
        ?
        Math.max(
            ...numbers
        ) + 1
        :
        1;


    return (
        `${prefix}-`
        +
        String(next)
            .padStart(
                6,
                "0"
            )
    );

}


/* =========================================================
   DOCUMENT NUMBER
========================================================= */

function generateDocumentNumber(
    prefix,
    collection
) {

    const year =
        new Date()
            .getFullYear();


    const start =
        `${prefix}-${year}-`;


    const numbers =
        collection
            .filter(
                item =>
                    String(
                        item.id
                    )
                    .startsWith(
                        start
                    )
            )
            .map(
                item =>
                    parseInt(
                        String(
                            item.id
                        )
                        .split("-")
                        .pop(),
                        10
                    )
            )
            .filter(
                Number.isFinite
            );


    const next =
        numbers.length
        ?
        Math.max(
            ...numbers
        ) + 1
        :
        1;


    return (
        start
        +
        String(next)
            .padStart(
                6,
                "0"
            )
    );

}


/* =========================================================
   GENERIC ID
========================================================= */

function generateId(
    prefix,
    collection
) {

    const values =
        collection
            .map(
                item =>
                    parseInt(
                        String(
                            item.id
                        )
                        .replace(
                            `${prefix}-`,
                            ""
                        ),
                        10
                    )
            )
            .filter(
                Number.isFinite
            );


    const next =
        values.length
        ?
        Math.max(
            ...values
        ) + 1
        :
        1;


    return (
        prefix
        +
        "-"
        +
        String(next)
            .padStart(
                6,
                "0"
            )
    );

}


/* =========================================================
   SHA256
========================================================= */

async function sha256(
    text
) {

    const bytes =
        new TextEncoder()
            .encode(
                text
            );


    const digest =
        await crypto.subtle.digest(
            "SHA-256",
            bytes
        );


    return Array
        .from(
            new Uint8Array(
                digest
            )
        )
        .map(
            byte =>
                byte
                    .toString(16)
                    .padStart(
                        2,
                        "0"
                    )
        )
        .join("");

}


/* =========================================================
   DATE
========================================================= */

function today() {

    return isoDate(
        new Date()
    );

}


function daysAgo(
    days
) {

    return isoDate(
        dateDaysAgo(
            days
        )
    );

}


function dateDaysAgo(
    days
) {

    const date =
        new Date();


    date.setHours(
        12,
        0,
        0,
        0
    );


    date.setDate(
        date.getDate() -
        days
    );


    return date;

}


function isoDate(
    date
) {

    const year =
        date.getFullYear();


    const month =
        String(
            date.getMonth() + 1
        )
        .padStart(
            2,
            "0"
        );


    const day =
        String(
            date.getDate()
        )
        .padStart(
            2,
            "0"
        );


    return (
        `${year}-${month}-${day}`
    );

}


/* =========================================================
   FORMAT
========================================================= */

function locale() {

    if (
        currentLanguage ===
        "uz"
    ) {

        return "uz-UZ";

    }


    if (
        currentLanguage ===
        "en"
    ) {

        return "en-US";

    }


    return "ru-RU";

}


function formatNumber(
    value
) {

    return new Intl
        .NumberFormat(
            locale()
        )
        .format(
            Number(value)
            ||
            0
        );

}


function money(
    value
) {

    return (
        formatNumber(
            Math.round(
                Number(value)
                ||
                0
            )
        )
        +
        " so'm"
    );

}


function compactMoney(
    value
) {

    const number =
        Number(value)
        ||
        0;


    if (
        number >=
        1000000000
    ) {

        return (
            (
                number /
                1000000000
            )
            .toFixed(1)
            +
            "B"
        );

    }


    if (
        number >=
        1000000
    ) {

        return (
            (
                number /
                1000000
            )
            .toFixed(1)
            +
            "M"
        );

    }


    if (
        number >=
        1000
    ) {

        return (
            (
                number /
                1000
            )
            .toFixed(0)
            +
            "K"
        );

    }


    return formatNumber(
        number
    );

}


function formatDate(
    value
) {

    if (
        !value
    ) {

        return "—";

    }


    const date =
        new Date(
            `${value}T12:00:00`
        );


    return new Intl
        .DateTimeFormat(
            locale()
        )
        .format(
            date
        );

}


function formatDateTime(
    value
) {

    if (
        !value
    ) {

        return "—";

    }


    return new Intl
        .DateTimeFormat(
            locale(),
            {
                dateStyle:
                    "short",

                timeStyle:
                    "short"
            }
        )
        .format(
            new Date(
                value
            )
        );

}


function longDate(
    date
) {

    return new Intl
        .DateTimeFormat(
            locale(),
            {
                weekday:
                    "long",

                day:
                    "numeric",

                month:
                    "long",

                year:
                    "numeric"
            }
        )
        .format(
            date
        );

}


function shortDay(
    date
) {

    return new Intl
        .DateTimeFormat(
            locale(),
            {
                weekday:
                    "short"
            }
        )
        .format(
            date
        )
        .replace(
            ".",
            ""
        );

}


/* =========================================================
   GENERIC HELPERS
========================================================= */

function valueOf(
    id
) {

    const element =
        document.getElementById(
            id
        );


    return element
        ?
        String(
            element.value
            ??
            ""
        )
        .trim()
        :
        "";

}


function numberValue(
    id
) {

    const number =
        Number(
            valueOf(
                id
            )
        );


    return Number.isFinite(
        number
    )
    ?
    number
    :
    0;

}


function setText(
    id,
    value
) {

    const element =
        document.getElementById(
            id
        );


    if (
        element
    ) {

        element.textContent =
            value;

    }

}


function setValue(
    id,
    value
) {

    const element =
        document.getElementById(
            id
        );


    if (
        element
    ) {

        element.value =
            value
            ??
            "";

    }

}


function normalize(
    value
) {

    return String(
        value
        ??
        ""
    )
    .trim()
    .toLowerCase();

}


function sum(
    collection,
    getter
) {

    return collection.reduce(
        (
            total,
            item
        ) =>
            total
            +
            Number(
                getter(item)
                ||
                0
            ),
        0
    );

}


function getInitials(
    value
) {

    return String(
        value
        ||
        "?"
    )
    .split(/\s+/)
    .filter(Boolean)
    .slice(
        0,
        2
    )
    .map(
        word =>
            word[0]
            .toUpperCase()
    )
    .join("");

}


function firstName(
    value
) {

    return (
        String(value)
            .split(/\s+/)
            .filter(Boolean)[0]
        ||
        value
    );

}


function escapeHtml(
    value
) {

    return String(
        value
        ??
        ""
    )
    .replace(
        /&/g,
        "&amp;"
    )
    .replace(
        /</g,
        "&lt;"
    )
    .replace(
        />/g,
        "&gt;"
    )
    .replace(
        /"/g,
        "&quot;"
    )
    .replace(
        /'/g,
        "&#039;"
    );

}


function emptyRow(
    colspan
) {

    return `
    <tr>

        <td
            colspan="${colspan}"
            class="empty-state"
        >
            ${escapeHtml(t("noData"))}
        </td>

    </tr>
    `;

}


function bindInput(
    id,
    callback
) {

    const element =
        document.getElementById(
            id
        );


    if (
        element
    ) {

        element.addEventListener(
            "input",
            callback
        );

    }

}


function bindChange(
    id,
    callback
) {

    const element =
        document.getElementById(
            id
        );


    if (
        element
    ) {

        element.addEventListener(
            "change",
            callback
        );

    }

}


/* =========================================================
   TOAST
========================================================= */

function showToast(
    title,
    message,
    type = "success"
) {

    const container =
        document.getElementById(
            "toastContainer"
        );


    const toast =
        document.createElement(
            "div"
        );


    toast.className =
        `toast ${type}`;


    toast.innerHTML =
        `

        <div class="toast-icon">
            ${
                type ===
                "error"
                ?
                "!"
                :
                "✓"
            }
        </div>

        <div class="toast-copy">

            <strong>
                ${escapeHtml(title)}
            </strong>

            <span>
                ${escapeHtml(message)}
            </span>

        </div>

        `;


    container.appendChild(
        toast
    );


    setTimeout(
        () => {

            toast.style.opacity =
                "0";

            toast.style.transform =
                "translateX(12px)";

        },
        3000
    );


    setTimeout(
        () => {

            toast.remove();

        },
        3350
    );

}