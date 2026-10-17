# Сборка APK для Lucky Casino (Windows + WSL2)

Проверено по документации Buildozer 1.6.0 (май 2026) и python-for-android master. Сам APK в окружении, где это писалось, собрать нельзя (нет Android SDK), поэтому при первой сборке возможны мелкие правки: пришли конец лога.

Файлы сборки:

- `buildozer.spec` - настройки (название, иконка, портрет, Kivy 2.3.1, только arm64)
- `build_android.sh` - копирует проект в WSL, собирает APK, кладёт его в папку `apk`
- `assets/android/` - иконка и заставка (`make_android_assets.py` пересоздаёт их, нужен Pillow)

## Что понадобится

- Windows 10/11, интернет, около 20 ГБ на диске C: (SDK, NDK и кэш качаются при первой сборке)
- Желательно 8 ГБ оперативной памяти

## Шаг 1. WSL2 и Ubuntu 24.04 (один раз)

В PowerShell от администратора:

```
wsl --install -d Ubuntu-24.04
```

Перезагрузись, если попросит, и задай имя и пароль в Ubuntu. Проверка: `wsl -l -v`, у Ubuntu должна стоять версия **2**. Нужна именно 24.04 (Python 3.12): на более новых Ubuntu с Python 3.14 сборка требует другой набор настроек.

## Шаг 2. Системные пакеты (один раз)

В Ubuntu:

```
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-venv python3-virtualenv autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev automake autopoint gettext rsync
```

Если Java стоит несколько версий, выбери 17: `sudo update-alternatives --config java` (и `javac`).

## Шаг 3. Сборка

```
sed -i 's/\r$//' /mnt/d/main/casino_origin/build_android.sh
bash /mnt/d/main/casino_origin/build_android.sh
```

Первая строка убирает Windows-переводы строк (в репозитории уже есть `.gitattributes`, который это предотвращает, но на всякий случай). Скрипт сам:

1. проверит Python, Java и нужные программы
2. поставит Buildozer в `~/buildozer-venv` (один раз)
3. скопирует проект в `~/casino_build`
4. соберёт APK и положит его в `D:\main\casino_origin\apk`
5. запишет полный лог в `build.log` рядом с проектом

Первая сборка долгая, не закрывай окно Ubuntu. Если оборвалась, просто запусти снова: скачанное не качается заново. После странных ошибок: `bash /mnt/d/main/casino_origin/build_android.sh clean`.

## Шаг 4. Установка на телефон

Скопируй файл из `apk` на телефон (кабель или Telegram себе), открой и разреши установку из этого источника. Это debug-версия для себя; для магазина нужна release-сборка с подписью и, по документации Buildozer, `p4a.branch = develop` с Python 3.14.

## Если что-то пошло не так

| Проблема | Что делать |
|---|---|
| `bad interpreter` или `\r` в ошибке | `sed -i 's/\r$//' build_android.sh` и запустить снова |
| Скрипт пишет, что нет программы или Java не 17 | Шаг 2 и `update-alternatives` |
| Ошибки про Cython | `~/buildozer-venv/bin/pip install "cython==0.29.34"` и запустить снова |
| Странные ошибки после неудачной сборки | `bash .../build_android.sh clean` |
| Не хватает места | Освободить диск C: |
| Ошибка про Rust или cargo | `curl https://sh.rustup.rs -sSf \| sh`, открыть новый терминал |
| `Aidl not found` | `rm -rf ~/.buildozer` и запустить снова, принять лицензии |

Если сборка падает, пришли **последние 50-100 строк** из `build.log`.

## Что проверить на телефоне

- Открывается в портрете на весь экран
- Есть звуки
- Баланс сохраняется после закрытия и открытия
- Кнопка «назад» на телефоне возвращает из игры в меню, а из меню закрывает приложение
- Если свернуть игру и вернуться, она не перезапускается
- Анимации и карты не тормозят
