/* =========================================================
   STORE FLOW
   AUTHORIZATION SYSTEM
   ========================================================= */


/* =========================================================
   CONFIG
   ========================================================= */

const AUTH_CONFIG = {

    USERS_KEY: "storeflow_users",

    SESSION_KEY: "storeflow_session",

    TEMP_SESSION_KEY: "storeflow_temp_session",

    THEME_KEY: "storeflow_theme",

    ATTEMPTS_KEY: "storeflow_login_attempts",

    MAX_ATTEMPTS: 5,

    LOCK_TIME: 30 * 1000,

    REDIRECT_AFTER_LOGIN: "index.html"

};


/* =========================================================
   DEFAULT USERS
   ========================================================= */

/*
    ДАННЫЕ ДЛЯ ВХОДА:

    СУПЕРАДМИНИСТРАТОР
    login: superadmin
    password: SuperAdmin@2026

    АДМИНИСТРАТОР
    login: admin
    password: Admin@2026


    В localStorage сохраняются НЕ пароли,
    а SHA-256 хэши.
*/

const DEFAULT_USERS = [

    {

        id: "USR-000001",

        fullName: "Суперадминистратор",

        username: "superadmin",

        passwordHash:
            "ef6129290c7d371da2598cd4c1e9725514397d18ebabca118c206df1ec6c5a11",

        role: "superadmin",

        roleName: "Суперадминистратор",

        active: true,

        permissions: ["*"],

        createdAt: "2026-09-08T00:00:00",

        lastLogin: null

    },


    {

        id: "USR-000002",

        fullName: "Администратор",

        username: "admin",

        passwordHash:
            "a36aef5a11c4073fbe60314fc9df530a9d5f986533594d1f5190742ff9e0e408",

        role: "admin",

        roleName: "Администратор",

        active: true,

        permissions: [

            "dashboard.view",

            "warehouse.view",

            "warehouse.manage",

            "products.view",

            "products.create",

            "products.edit",

            "imports.view",

            "imports.create",

            "sales.view",

            "sales.create",

            "counterparties.view",

            "counterparties.create",

            "counterparties.edit",

            "reports.view",

            "users.view"

        ],

        createdAt: "2026-09-08T00:00:00",

        lastLogin: null

    }

];


/* =========================================================
   ELEMENTS
   ========================================================= */

const loginForm =
    document.getElementById("loginForm");

const usernameInput =
    document.getElementById("username");

const passwordInput =
    document.getElementById("password");

const rememberMe =
    document.getElementById("rememberMe");

const loginButton =
    document.getElementById("loginButton");

const passwordToggle =
    document.getElementById("passwordToggle");

const usernameError =
    document.getElementById("usernameError");

const passwordError =
    document.getElementById("passwordError");

const loginMessage =
    document.getElementById("loginMessage");

const loginMessageText =
    document.getElementById("loginMessageText");

const closeMessage =
    document.getElementById("closeMessage");

const capsWarning =
    document.getElementById("capsWarning");

const themeToggle =
    document.getElementById("themeToggle");

const successOverlay =
    document.getElementById("successOverlay");

const successUserName =
    document.getElementById("successUserName");


/* =========================================================
   INITIALIZATION
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        initializeUsers();

        initializeTheme();

        checkExistingSession();

        restoreRememberedUsername();

        usernameInput.focus();

    }
);


/* =========================================================
   USERS INITIALIZATION
   ========================================================= */

function initializeUsers() {

    let savedUsers = [];

    try {

        const storedUsers =
            localStorage.getItem(
                AUTH_CONFIG.USERS_KEY
            );

        if (storedUsers) {

            savedUsers =
                JSON.parse(storedUsers);

        }

    } catch (error) {

        console.error(
            "Ошибка чтения пользователей:",
            error
        );

        savedUsers = [];

    }


    if (!Array.isArray(savedUsers)) {

        savedUsers = [];

    }


    /*
        Добавляем стандартных пользователей,
        если их еще нет.

        Уже существующих пользователей
        не перезаписываем.
    */

    DEFAULT_USERS.forEach(
        defaultUser => {

            const exists =
                savedUsers.some(
                    user =>
                        user.username
                            .toLowerCase()
                        ===
                        defaultUser.username
                            .toLowerCase()
                );

            if (!exists) {

                savedUsers.push(
                    defaultUser
                );

            }

        }
    );


    localStorage.setItem(
        AUTH_CONFIG.USERS_KEY,
        JSON.stringify(savedUsers)
    );

}


/* =========================================================
   SHA-256
   ========================================================= */

async function sha256(text) {

    if (
        !window.crypto ||
        !window.crypto.subtle
    ) {

        throw new Error(
            "Web Crypto API недоступен. Откройте проект через VS Code Live Server."
        );

    }


    const encoder =
        new TextEncoder();

    const data =
        encoder.encode(text);

    const hashBuffer =
        await crypto.subtle.digest(
            "SHA-256",
            data
        );


    const hashArray =
        Array.from(
            new Uint8Array(
                hashBuffer
            )
        );


    return hashArray
        .map(
            byte =>
                byte
                    .toString(16)
                    .padStart(2, "0")
        )
        .join("");

}


/* =========================================================
   LOGIN SUBMIT
   ========================================================= */

loginForm.addEventListener(
    "submit",
    async event => {

        event.preventDefault();


        clearErrors();

        hideMessage();


        if (isLocked()) {

            const remaining =
                getRemainingLockSeconds();

            showMessage(
                `Слишком много попыток входа. Повторите через ${remaining} сек.`
            );

            shakeForm();

            return;

        }


        const username =
            usernameInput.value
                .trim();

        const password =
            passwordInput.value;


        /* -----------------------------------------
           VALIDATION
        ----------------------------------------- */

        let valid = true;


        if (!username) {

            setFieldError(
                usernameInput,
                usernameError,
                "Введите логин"
            );

            valid = false;

        }


        if (!password) {

            setFieldError(
                passwordInput,
                passwordError,
                "Введите пароль"
            );

            valid = false;

        }


        if (!valid) {

            shakeForm();

            return;

        }


        setLoading(true);


        try {

            /*
                Небольшая задержка для
                плавного UI.
            */

            await sleep(450);


            const users =
                getUsers();


            const user =
                users.find(
                    currentUser =>
                        currentUser.username
                            .toLowerCase()
                        ===
                        username.toLowerCase()
                );


            /* -------------------------------------
               USER NOT FOUND
            ------------------------------------- */

            if (!user) {

                registerFailedAttempt();

                showInvalidCredentials();

                return;

            }


            /* -------------------------------------
               USER BLOCKED
            ------------------------------------- */

            if (!user.active) {

                showMessage(
                    "Данная учетная запись заблокирована. Обратитесь к администратору."
                );

                shakeForm();

                return;

            }


            /* -------------------------------------
               PASSWORD HASH
            ------------------------------------- */

            const enteredPasswordHash =
                await sha256(password);


            if (
                enteredPasswordHash
                !==
                user.passwordHash
            ) {

                registerFailedAttempt();

                showInvalidCredentials();

                return;

            }


            /* -------------------------------------
               SUCCESS
            ------------------------------------- */

            resetFailedAttempts();


            user.lastLogin =
                new Date()
                    .toISOString();


            saveUpdatedUser(user);


            createSession(
                user,
                rememberMe.checked
            );


            if (
                rememberMe.checked
            ) {

                localStorage.setItem(
                    "storeflow_remembered_username",
                    user.username
                );

            } else {

                localStorage.removeItem(
                    "storeflow_remembered_username"
                );

            }


            successUserName.textContent =
                `Добро пожаловать, ${user.fullName}`;


            successOverlay.classList.add(
                "show"
            );


            await sleep(1100);


            window.location.href =
                AUTH_CONFIG.REDIRECT_AFTER_LOGIN;


        } catch (error) {

            console.error(error);


            showMessage(
                error.message ||
                "Произошла ошибка авторизации."
            );

        } finally {

            setLoading(false);

        }

    }
);


/* =========================================================
   INVALID CREDENTIALS
   ========================================================= */

function showInvalidCredentials() {

    const remaining =
        AUTH_CONFIG.MAX_ATTEMPTS
        -
        getAttemptCount();


    if (remaining <= 0) {

        showMessage(
            "Слишком много неверных попыток. Вход временно заблокирован на 30 секунд."
        );

    } else {

        showMessage(
            `Неверный логин или пароль. Осталось попыток: ${remaining}.`
        );

    }


    passwordInput.value = "";

    passwordInput.focus();

    shakeForm();

}


/* =========================================================
   USERS
   ========================================================= */

function getUsers() {

    try {

        return JSON.parse(
            localStorage.getItem(
                AUTH_CONFIG.USERS_KEY
            )
        ) || [];

    } catch {

        return [];

    }

}


/* =========================================================
   UPDATE USER
   ========================================================= */

function saveUpdatedUser(
    updatedUser
) {

    const users =
        getUsers();


    const index =
        users.findIndex(
            user =>
                user.id
                ===
                updatedUser.id
        );


    if (index === -1) {

        return;

    }


    users[index] =
        updatedUser;


    localStorage.setItem(
        AUTH_CONFIG.USERS_KEY,
        JSON.stringify(users)
    );

}


/* =========================================================
   CREATE SESSION
   ========================================================= */

function createSession(
    user,
    remember
) {

    const session = {

        userId:
            user.id,

        username:
            user.username,

        fullName:
            user.fullName,

        role:
            user.role,

        roleName:
            user.roleName,

        permissions:
            user.permissions,

        loggedIn:
            true,

        loginAt:
            new Date()
                .toISOString()

    };


    if (remember) {

        localStorage.setItem(
            AUTH_CONFIG.SESSION_KEY,
            JSON.stringify(session)
        );


        sessionStorage.removeItem(
            AUTH_CONFIG.TEMP_SESSION_KEY
        );

    } else {

        sessionStorage.setItem(
            AUTH_CONFIG.TEMP_SESSION_KEY,
            JSON.stringify(session)
        );


        localStorage.removeItem(
            AUTH_CONFIG.SESSION_KEY
        );

    }

}


/* =========================================================
   CHECK EXISTING SESSION
   ========================================================= */

function checkExistingSession() {

    const persistentSession =
        localStorage.getItem(
            AUTH_CONFIG.SESSION_KEY
        );


    const temporarySession =
        sessionStorage.getItem(
            AUTH_CONFIG.TEMP_SESSION_KEY
        );


    const rawSession =
        persistentSession
        ||
        temporarySession;


    if (!rawSession) {

        return;

    }


    try {

        const session =
            JSON.parse(rawSession);


        if (
            session &&
            session.loggedIn
        ) {

            window.location.href =
                AUTH_CONFIG.REDIRECT_AFTER_LOGIN;

        }

    } catch {

        localStorage.removeItem(
            AUTH_CONFIG.SESSION_KEY
        );

        sessionStorage.removeItem(
            AUTH_CONFIG.TEMP_SESSION_KEY
        );

    }

}


/* =========================================================
   REMEMBER USERNAME
   ========================================================= */

function restoreRememberedUsername() {

    const remembered =
        localStorage.getItem(
            "storeflow_remembered_username"
        );


    if (!remembered) {

        return;

    }


    usernameInput.value =
        remembered;


    rememberMe.checked =
        true;


    passwordInput.focus();

}


/* =========================================================
   FAILED ATTEMPTS
   ========================================================= */

function getAttemptsData() {

    try {

        const stored =
            sessionStorage.getItem(
                AUTH_CONFIG.ATTEMPTS_KEY
            );


        if (!stored) {

            return {

                count: 0,

                lockedUntil: null

            };

        }


        return JSON.parse(
            stored
        );

    } catch {

        return {

            count: 0,

            lockedUntil: null

        };

    }

}


/* =========================================================
   REGISTER FAILED ATTEMPT
   ========================================================= */

function registerFailedAttempt() {

    const data =
        getAttemptsData();


    data.count =
        (data.count || 0) + 1;


    if (
        data.count
        >=
        AUTH_CONFIG.MAX_ATTEMPTS
    ) {

        data.lockedUntil =
            Date.now()
            +
            AUTH_CONFIG.LOCK_TIME;

    }


    sessionStorage.setItem(
        AUTH_CONFIG.ATTEMPTS_KEY,
        JSON.stringify(data)
    );

}


/* =========================================================
   GET ATTEMPT COUNT
   ========================================================= */

function getAttemptCount() {

    return (
        getAttemptsData().count
        ||
        0
    );

}


/* =========================================================
   LOCK CHECK
   ========================================================= */

function isLocked() {

    const data =
        getAttemptsData();


    if (!data.lockedUntil) {

        return false;

    }


    if (
        Date.now()
        >=
        data.lockedUntil
    ) {

        resetFailedAttempts();

        return false;

    }


    return true;

}


/* =========================================================
   LOCK REMAINING
   ========================================================= */

function getRemainingLockSeconds() {

    const data =
        getAttemptsData();


    if (!data.lockedUntil) {

        return 0;

    }


    return Math.max(
        0,
        Math.ceil(
            (
                data.lockedUntil
                -
                Date.now()
            )
            /
            1000
        )
    );

}


/* =========================================================
   RESET ATTEMPTS
   ========================================================= */

function resetFailedAttempts() {

    sessionStorage.removeItem(
        AUTH_CONFIG.ATTEMPTS_KEY
    );

}


/* =========================================================
   PASSWORD VISIBILITY
   ========================================================= */

passwordToggle.addEventListener(
    "click",
    () => {

        const isPassword =
            passwordInput.type
            ===
            "password";


        passwordInput.type =
            isPassword
                ? "text"
                : "password";


        passwordToggle.classList.toggle(
            "visible",
            isPassword
        );


        passwordToggle.setAttribute(
            "aria-label",
            isPassword
                ? "Скрыть пароль"
                : "Показать пароль"
        );


        passwordInput.focus();

    }
);


/* =========================================================
   CAPS LOCK
   ========================================================= */

passwordInput.addEventListener(
    "keyup",
    event => {

        if (
            event.getModifierState
            &&
            event.getModifierState(
                "CapsLock"
            )
        ) {

            capsWarning.classList.add(
                "show"
            );

        } else {

            capsWarning.classList.remove(
                "show"
            );

        }

    }
);


passwordInput.addEventListener(
    "blur",
    () => {

        capsWarning.classList.remove(
            "show"
        );

    }
);


/* =========================================================
   REMOVE FIELD ERROR ON INPUT
   ========================================================= */

usernameInput.addEventListener(
    "input",
    () => {

        removeFieldError(
            usernameInput,
            usernameError
        );

        hideMessage();

    }
);


passwordInput.addEventListener(
    "input",
    () => {

        removeFieldError(
            passwordInput,
            passwordError
        );

        hideMessage();

    }
);


/* =========================================================
   FIELD ERRORS
   ========================================================= */

function setFieldError(
    input,
    errorElement,
    message
) {

    input
        .closest(
            ".input-wrapper"
        )
        .classList.add(
            "error"
        );


    errorElement.textContent =
        message;

}


/* =========================================================
   REMOVE ERROR
   ========================================================= */

function removeFieldError(
    input,
    errorElement
) {

    input
        .closest(
            ".input-wrapper"
        )
        .classList.remove(
            "error"
        );


    errorElement.textContent =
        "";

}


/* =========================================================
   CLEAR ERRORS
   ========================================================= */

function clearErrors() {

    removeFieldError(
        usernameInput,
        usernameError
    );


    removeFieldError(
        passwordInput,
        passwordError
    );

}


/* =========================================================
   LOGIN MESSAGE
   ========================================================= */

function showMessage(
    message,
    type = "error"
) {

    loginMessageText.textContent =
        message;


    loginMessage.classList.remove(
        "success"
    );


    if (
        type === "success"
    ) {

        loginMessage.classList.add(
            "success"
        );

    }


    loginMessage.classList.add(
        "show"
    );

}


/* =========================================================
   HIDE MESSAGE
   ========================================================= */

function hideMessage() {

    loginMessage.classList.remove(
        "show"
    );

}


/* =========================================================
   CLOSE MESSAGE
   ========================================================= */

closeMessage.addEventListener(
    "click",
    hideMessage
);


/* =========================================================
   LOADING
   ========================================================= */

function setLoading(
    state
) {

    loginButton.disabled =
        state;


    loginButton.classList.toggle(
        "loading",
        state
    );

}


/* =========================================================
   SHAKE FORM
   ========================================================= */

function shakeForm() {

    const loginBox =
        document.querySelector(
            ".login-box"
        );


    loginBox.classList.remove(
        "shake"
    );


    void loginBox.offsetWidth;


    loginBox.classList.add(
        "shake"
    );


    setTimeout(
        () => {

            loginBox.classList.remove(
                "shake"
            );

        },
        400
    );

}


/* =========================================================
   THEME
   ========================================================= */

function initializeTheme() {

    const savedTheme =
        localStorage.getItem(
            AUTH_CONFIG.THEME_KEY
        );


    if (
        savedTheme === "dark"
    ) {

        document.body.classList.add(
            "dark-theme"
        );

        return;

    }


    if (
        savedTheme === "light"
    ) {

        document.body.classList.remove(
            "dark-theme"
        );

        return;

    }


    /*
        Если пользователь еще не выбирал тему,
        учитываем системные настройки.
    */

    if (
        window.matchMedia
        &&
        window.matchMedia(
            "(prefers-color-scheme: dark)"
        ).matches
    ) {

        document.body.classList.add(
            "dark-theme"
        );

    }

}


/* =========================================================
   THEME BUTTON
   ========================================================= */

themeToggle.addEventListener(
    "click",
    () => {

        document.body
            .classList.toggle(
                "dark-theme"
            );


        const isDark =
            document.body
                .classList
                .contains(
                    "dark-theme"
                );


        localStorage.setItem(
            AUTH_CONFIG.THEME_KEY,
            isDark
                ? "dark"
                : "light"
        );

    }
);


/* =========================================================
   UTILITIES
   ========================================================= */

function sleep(ms) {

    return new Promise(
        resolve =>
            setTimeout(
                resolve,
                ms
            )
    );

}