# Design handoff: D&D Character Builder

Документ за дизайнер-асистент (друг Claude модел, без памет за проекта). Собственикът го подава в нов чат. Всичко, което
дизайнерът трябва да знае за приложението, ограниченията и начина на работа, е тук. Пътищата са от корена на хранилището
`/Users/yoanpetrov/dnd-character-creator` (по-нататък `<repo>`).

## Съдържание

1. [Какво е приложението и кой го ползва](#1-какво-е-приложението-и-кой-го-ползва)
2. [Изискването на собственика към дизайна](#2-изискването-на-собственика-към-дизайна)
3. [Карта на страниците](#3-карта-на-страниците)
4. [Дизайн куките, които вече съществуват](#4-дизайн-куките-които-вече-съществуват)
5. [Твърди ограничения и пазачи (guards)](#5-твърди-ограничения-и-пазачи-guards)
6. [Какво НЕ се променя](#6-какво-не-се-променя)
7. [Как се пуска, тества, строи и публикува](#7-как-се-пуска-тества-строи-и-публикува)
8. [Възможности за дизайн](#8-възможности-за-дизайн)
9. [Речник на D&D термините в интерфейса](#9-речник-на-dd-термините-в-интерфейса)

---

## 1. Какво е приложението и кой го ползва

**Създаване на герои за D&D 5e** (Dungeons & Dragons, ролева игра на маса). Потребителят избира клас, произход
(Background), раса (Species), характеристики (Ability Scores) и екипировка, а приложението изчислява цял лист на героя и го
изнася като PDF, Markdown или YAML. Правилата са 2024 Player's Handbook (и SRD); има и режим 2014.

- **Кой го ползва:** собственикът и близки приятели. Не е публичен продукт, няма акаунти, няма сървър за данни.
- **Устройства:** телефон на първо място (iPhone Safari е главната цел), после десктоп.
- **Работи изцяло офлайн** като инсталируемо PWA. Енджинът (Python правилата) тръгва в браузъра през Pyodide (WebAssembly)
  в Web Worker. След първото посещение (около 18 MB изтегляне) работи и в самолетен режим.
- **Адрес:** https://yoanpetroshan.github.io/dnd-character-creator/ (GitHub Pages, под-път `/dnd-character-creator/`).
- **Данните на героите** стоят само в `localStorage` на устройството (библиотека от герои + чернова за всеки). Нищо не се
  праща никъде.
- **Езици:** интерфейсът е на **български**, като правилните термини са с английския термин в скоби, напр.
  `Талант (Feat)`, `Клас броня (Armor Class, AC)`. Има и чисто **английски** режим. Превключвател BG / EN в хедъра.
  Имената на класове, раси, умения, заклинания и предмети идват от данните и остават на английски и в двата езика.
- **Технологии:** React 19, react-router-dom 7, TypeScript, Vite 8, vitest. Без UI библиотека, без CSS framework, без
  Tailwind. Целият вид живее в обикновен CSS (`frontend/src/styles/*.css`). Днешният вид е нарочно гол (system-ui, сиви
  кутии, синьо ударение): има какво да се проектира от нулата.

Обща форма на потребителското пътуване: Home (име на героя, библиотека) → Class → Background → Species → Abilities →
Equipment → Sheet (преглед) → Export. Лентата със стъпки е винаги отгоре; най-долу на всяка страница има бутон "Напред".

## 2. Изискването на собственика към дизайна

Собственикът иска (по смисъл, дословно по намерение):

> **Отличителен, запомнящ се дизайн, който НЕ е генеричен "AI slop" уебсайт.** Без стандартни градиенти, без лилаво, без
> glassmorphism, без шаблонни "hero" секции, без генерични решетки от карти. Приложението да има собствено лице и
> характер, подходящо за настолна ролева игра, а не да прилича на всеки друг SaaS шаблон.

Правила на играта:

- **Дизайнът се прави сега и само сега.** Логиката е завършена и **замразена**: енджин, данни, API, тестове, golden и
  baseline файлове не се пипат (виж раздел 6). Всичко визуално е работа по CSS, шрифтове, изображения и (внимателно)
  разметка.
- Предпочитаният начин е **само CSS** (токени и таблици със стилове): тогава нищо в тестовете не се мести. Промяна на
  JSX разметката е позволена, но струва повторно заснемане на snapshot (раздел 5.3). Ако дизайнът налага нова обвивка или
  нов елемент, прави се умишлено и докладва.
- Дизайнерът решава посоката (типография, палитра, форма на компонентите, рамки, декор, иконография), но трябва да я
  обоснове накратко и да покаже резултата визуално на 375 px, преди да я прилага навсякъде.
- Не копирай стил на съществуващ продукт или марка (включително официалния стил на Wizards of the Coast / D&D Beyond).
  Не са позволени и защитени изображения, лога и шрифтове без свободен лиценз; всеки добавен шрифт или картинка трябва да
  е с лиценз, позволяващ вграждане, и лицензът да се запише (като `LICENSE` до файла).

## 3. Карта на страниците

Рутер: `frontend/src/App.tsx`. Маршрути (всички под basename `import.meta.env.BASE_URL`; `/` и непознат път водят към `/home`):

| Маршрут | Файл | Етикет на стъпка (bg / en) |
| --- | --- | --- |
| `/home` | `frontend/src/pages/HomePage.tsx` | Home / Home |
| `/class` | `.../ClassPage.tsx` | Клас / Class |
| `/background` | `.../BackgroundPage.tsx` | Произход (Background) / Background |
| `/species` | `.../SpeciesPage.tsx` | Раса (Species) / Species |
| `/abilities` | `.../AbilitiesPage.tsx` | Abilities / Abilities |
| `/equipment` | `.../EquipmentPage.tsx` | Equipment / Equipment |
| `/sheet` | `.../SheetPage.tsx` | Лист / Sheet |
| `/export` | `.../ExportPage.tsx` | Export / Export |
| `/help` | `.../HelpPage.tsx` | Помощ / Help (линк в хедъра, не е стъпка) |

(Етикетите идват от `frontend/src/copy/bg.ts` и `en.ts`, ключ `nav.steps`; редът на стъпките е в
`frontend/src/logic/steps.ts`, масив `STEPS`.)

### 3.1 Черупката около всяка страница (`App.tsx`)

Редът на елементите отгоре надолу:

1. `header.app-header`: линк `a.help-link` (към `/help`) и `div.lang-switch` (`LanguageSwitch`: два бутона BG и EN,
   `aria-pressed`, `data-state="active|inactive"`).
2. `nav.step-nav` (`StepNav`): хоризонтално скролиращи се линкове към 8-те стъпки. Активната има класа `active`. Значка
   `span.step-nav__badge` с число се показва само когато в стъпката има неразрешени неща (избори, проблеми, липсваща част).
3. `NextStepLink`: линк "Следваща неприключена стъпка →" (към първата стъпка с нещо отворено, иначе към Export).
4. `NewChoicesLink`: линк `a.new-choices` "Нови избори: N" (след вдигане на ниво).
5. `StatusBanner`: статус редове (виж 3.5).
6. `main` с маршрутизираната страница (`div.page`) и най-долу `a.next-button` (`NextStepButton`).

`ErrorBoundary` обгръща страницата (срив на една страница не чупи навигацията).

### 3.2 Стъпка по стъпка

**Home** (`/home`). Име на героя (поле + бутон `button.name-dice` със зарче за случайно име), библиотека на героите
(списък: отвори / преименуй / дублирай / изтрий, нов герой, "Изтегли всички (.json)", качване на .json, отчет за
импорта със `data-status="accepted|rejected"`), раздел "Правила и източници" (ruleset: Mixed / 2014 / 2024, избор на
книги), списък на "изпаднали" избори (`data-state="pruned"`). Активният герой в списъка е с `data-active="true"`.

**Class** (`/class`). Един или повече класове (`div.class-block`), добавяне на клас (`.add-class`), ниво (число с
`CommitNumberInput`), подклас, зарове за точки живот (`.hp-rolls`, `.hp-summary`), подсказка за по-високи нива
(`.higher-levels-teaser`). Табове (`div.tab-bar[role=tablist]`, бутони `role=tab` с `aria-selected`) "Features" и
"Spells" (само за заклинателите). Карти с избори (`ChoiceCard`) за умения, избор на подклас, черти (Feat) и др.
Обобщения: `ClassResourcesList` (`.class-resources`), `SpellSlotsSummary`, `SpellLibrary` (разглеждане на трикове и
заклинания с `details`).

**Background** (`/background`). Избор на произход и неговите карти с избори (умения, езици, инструменти, черта). Секции
`.details-section` (свиваеми).

**Species** (`/species`). Избор на раса, подраса/вариант и картите към тях. Филтър `.picker-filter`, списък
`.picker-list`.

**Abilities** (`/abilities`). Метод: `.ability-method-selector` с радио бутони Standard Array / Point Buy / Roll (4d6,
drop lowest) / Manual. Таблица `.ability-table` (шест характеристики: STR, DEX, CON, INT, WIS, CHA; базова стойност,
бонуси, краен резултат, модификатор), стъпало за покупка на точки `.point-buy-stepper`, останали точки.

**Equipment** (`/equipment`). Секции `.equipment-section`: карти с избор на начална екипировка (при класа, "(a) или (b)"),
браузър на предмети (`.item-browser-list`, скролируем списък с чекбоксове и филтър), инвентар (`.inventory-list`),
носено/държано, злато.

**Sheet** (`/sheet`). Само за четене лист на героя, `SheetView` от 23 секции (виж 3.4). Горе има бутон "Печат" (`window.print()`), линк към Export и ред за
неприключени неща; те са с `.no-print`. Страницата е `div.page[data-page="sheet"]`.

**Export** (`/export`). Проверка за готовност (какво още липсва, с линкове към картите), обобщения (`ClassResourcesList`,
`SpellSlotsSummary`, `SheetTraitsSummary`), бутони за YAML / Markdown / PDF (`data-state="ready|busy|disabled"`), ред с
грешка (`.status--error`, `data-state="error"`), ред "подготвям PDF" (`p[data-state="preparing-pdf"]`, `role=status`).

**Help** (`/help`, `div.page.help-page`). Блокове с `data-section`: `offline` (състояние на офлайн, редът има
`data-state="idle|unsupported|installing|offline-ready|update-available|error"`, редът за паметта
`data-state="granted|denied"`), `install` (стъпки за iPhone Safari, Android Chrome, десктоп), `keep` (7-дневно
изтриване на данните на iOS + линк към архивиране от Home), `troubleshooting` (Lockdown Mode и др.). Само текст.

### 3.3 Карти с избори и избирачи (най-често срещаният компонент)

Файлове: `frontend/src/components/ChoiceCard.tsx`, `ChoicePicker.tsx`.

Сървърът (енджинът) връща списък от "избори" (`Choice`: `id`, `label`, `description`, `status`, `count`, `selected`,
`options[]`). Всеки е `div.choice-card` с:

- заглавен бутон `button.choice-card__header` (`aria-expanded`): `.choice-card__pending-dot` (кръгче "!" само при
  непотвърден задължителен избор), `.choice-card__label`, `.choice-card__new` ("ново", само при `data-new="true"`),
  `.choice-card__level` (ниво), `.choice-card__count` (избрани/нужни, напр. 1/2);
- тяло `.choice-card__body` (само когато е разтворена): описание, причина при `unavailable`, "Дава: ...", избирач.

Избирачът (`ChoicePicker`) има три вида според броя опции:

| Вид | Кога | Разметка |
| --- | --- | --- |
| **Къс** (ShortPicker) | до 30 опции | `ul.choice-picker`; чекбокс във всяка `li`; над 20 опции се появява филтър `input.picker-filter`; бутон `.choice-picker__toggle-unavailable` показва/скрива недостъпните; заглавия на групи `span.choice-picker__group` |
| **Дълъг** (LongPicker) | над 30 опции (напр. заклинания) | групи (по ниво на заклинание) като акордеон: бутон `.choice-picker__group-toggle` (`aria-expanded`), блок "Избрано" (`.choice-picker__selected`, `.choice-picker__selected-list`), избор на книга `select.picker-source`, филтър, брояч на резултатите `.choice-picker__result-count` |
| **Акордеон на картата** | всяка карта | `data-state="expanded|collapsed"`, отворена по подразбиране е само първата непотвърдена |

Константи: `FILTER_THRESHOLD = 20`, `LONG_LIST_THRESHOLD = 30` в `ChoicePicker.tsx`. Ред от опция: `li[data-state=...]` >
`label` > `input[type=checkbox]` + текст + (`span.choice-picker__reason` с причина за недостъпност).

### 3.4 Листът (`/sheet`): 23 секции

`frontend/src/components/sheet/SheetView.tsx` рисува секциите по ред. Всяка е `section[data-section="<ключ>"]` с
`h2` (`SectionFrame.tsx`). Ключовете (в реда на листа, от `frontend/src/logic/sheetSections.ts`):

1. `identity` (име, ниво, класове, раса, произход)
2. `abilities` (шестте характеристики и модификатори)
3. `proficiencyBonus`
4. `armorClass`
5. `hitPoints` (макс. и Hit Dice)
6. `initiative`
7. `speeds`
8. `senses`
9. `passives` (пасивно възприятие/проницателност/разследване)
10. `savingThrows`
11. `skills` (таблица с умения, владеене, експертиза)
12. `proficiencies` (броня, оръжия, инструменти)
13. `languages`
14. `attacks` (атаки, оръжейно майсторство)
15. `resources` (ресурси на клас/черта/раса, напр. Rage, Ki)
16. `features` (умения на класа и расата, групирани)
17. `feats` (Таланти)
18. `spells` (заклинатели, слотове, списъци)
19. `innateSpells` (вродени заклинания)
20. `equipment` (групи предмети, носено)
21. `carryingCapacity`
22. `defenses` (съпротиви, имунитети, уязвимости)
23. `details` (външност, личност и пр.)

Таблиците в секциите са с `overflow-x: auto` (`touch.css`), дългите текстове се пренасят (`overflow-wrap: anywhere`).
Листът е най-голямата възможност за "лист на герой" оформление (раздел 8).

### 3.5 Статус банери (`StatusBanner.tsx`)

Всеки е `p.status-banner` с `data-state` (само един атрибут състояние на елемент). Оформя се по `[data-state="..."]`.

| `data-state` | Кога | Роля |
| --- | --- | --- |
| `engine-starting` | енджинът в браузъра се стартира | `status` |
| `engine-unavailable` | няма WebAssembly/Worker (iOS Lockdown Mode), пакетът не се свали; линк към Help | `alert` |
| `pwa-installing` | първото посещение сваля кеша (около 20 MB) | `status` |
| `offline-ready` | веднъж след инсталацията; бутон "Затвори" | `status` |
| `update-available` | чака нова версия; бутон "Обнови сега" | `status` |
| `error` | неуспешно изчисляване (последният добър лист остава); бутон "Опитай пак" | `alert` |
| `notice` | съобщения (напр. повредена чернова); линк за сваляне, копиране, "Затвори" | `status` |
| `storage-failed` | браузърът не позволява запис в `localStorage` | `status` |
| `server-older` | версията на сървъра е по-стара от приложението (само при Flask режим) | `status` |
| `pruned` | сървърът е изхвърлил избори; линк към Home | `status` |

### 3.6 Печат

`frontend/src/print.css` (внася се от `main.tsx`, не от `index.css`): при `@media print` скрива `.step-nav`, `.next-step`,
`.next-button`, `.status-banner`, `.no-print` и всички `button`. Днес печатът е само "листът без хрома". PDF изнасянето
е отделно (виж 5.7): прави го енджинът със собствен шаблон.

### 3.7 Таблица на състоянията (`data-*` куки)

Копирана от `docs/FRONTEND-STRUCTURE.md` (там е и актуалният оригинал).

- `data-status` = състоянието на нещо според сървъра (избор `pending|resolved|unavailable`, запис от отчета за импорт
  `accepted|rejected`).
- `data-state` = състояние на интерфейса, една стойност на елемент:
  - карта с избор: `expanded | collapsed`
  - ред с опция в избирач: `available | disabled | hidden-by-filters`
  - статус банер: `error | notice | storage-failed | server-older | pruned | engine-starting | engine-unavailable |
    pwa-installing | update-available | offline-ready` (последните четири само в офлайн билда)
  - изпаднал избор в списъка на Home: `pruned`
  - бутон за изнасяне: `ready | busy | disabled`; ред с грешка при изнасяне: `error`; ред "подготвям PDF" (само офлайн,
    първи PDF): `preparing-pdf`
  - бутон за език: `active | inactive`
  - ред за офлайн състоянието в Help: `idle | unsupported | installing | offline-ready | update-available | error`;
    редът за паметта под него: `granted | denied`
- `data-new="true"` маркира непотвърдена карта (и хедър линка `.new-choices`), появила се след вдигане на ниво. Картата
  съдържа и `span.choice-card__new`. Атрибутът липсва иначе.
- `a.next-button` (`NextStepButton`): води към стъпката СЛЕД текущата във фиксирания ред на `STEPS`. `data-next="<ключ
  на целевата стъпка>"` (`class`, `background`, ...), `aria-label` "Напред: <име на стъпката>" / "Next: <step name>".
  Няма атрибут за състояние; липсва на Export (последна стъпка), на Help и на непознати маршрути; 44 px в `touch.css`,
  празно правило в `hooks.css`, скрит при печат. Натискането скролира най-горе.
- Линкът в навигацията по стъпки пази класа `active` (react-router); значката `step-nav__badge` е само при неразрешени
  стъпки. `data-active="true"` маркира активния герой в списъка на Home.
- Цветове: `status--error` за текст на грешка. Бележката `choice-pruned` е дефинирана в CSS, но още не се рисува от
  компонент.

Състояния, които дизайнът трябва да покрие (от `docs/FRONTEND-STRUCTURE.md`): pending (синя лява рамка и "!" точка,
значка на стъпката), resolved, unavailable (причина в тялото), optional (непотвърден незадължителен: без "!"), disabled
(сив етикет + причина), hidden-by-filters (само след "покажи недостъпните"), pruned, new, loading/error (заглавията
показват "…" докато се изчислява), preparing PDF, engine unavailable, offline install/update, engine starting.

## 4. Дизайн куките, които вече съществуват

### 4.1 Файлове със стилове и редът им

`frontend/src/index.css` съдържа САМО `@import` на тези файлове, в този ред (редът е каскадата, пази го):

| # | Файл | Съдържание |
| --- | --- | --- |
| 1 | `frontend/src/styles/tokens.css` | `:root` променливи (4.2) |
| 2 | `frontend/src/styles/base.css` | `box-sizing`, `body`, `.app` |
| 3 | `frontend/src/styles/layout.css` | `.app-header`, `.lang-switch`, `.step-nav`, `main`, `.page` |
| 4 | `frontend/src/styles/status.css` | `.status--error` |
| 5 | `frontend/src/styles/choice.css` | карти с избори, избирачи |
| 6 | `frontend/src/styles/abilities.css` | метод на характеристиките, таблица, стъпало |
| 7 | `frontend/src/styles/lists.css` | екипировка, браузър на предмети, инвентар, табове |
| 8 | `frontend/src/styles/spells.css` | библиотека със заклинания |
| 9 | `frontend/src/styles/forms.css` | `.details-section`, зарове за HP, `.class-block`, `.choice-pruned` |
| 10 | `frontend/src/styles/touch.css` | мобилни/докосване правила (функционални, вж. 4.4) |
| 11 | `frontend/src/styles/hooks.css` | празни правила за класове без стил още |
| - | `frontend/src/print.css` | печат (внася се от `main.tsx`) |

Все още няма стил за `.status-banner` (банерите са голи `<p>`), за секциите на листа (`[data-section]` има само
структурни правила), за `.help-page`, `.next-button` (само размер) и за заглавията `h1`/`h2`. Това е най-голямата
"бяла" територия.

### 4.2 Токени (`frontend/src/styles/tokens.css`, сегашни стойности)

| Токен | Стойност | Забележка |
| --- | --- | --- |
| `--font-sans` | `system-ui, sans-serif` | единственият шрифтов токен |
| `--space-1` | `4px` | |
| `--space-2` | `8px` | |
| `--space-3` | `12px` | |
| `--space-4` | `16px` | |
| `--space-5` | `20px` | |
| `--radius-sm` | `4px` | |
| `--radius-pill` | `10px` | значки |
| `--radius-round` | `50%` | точки |
| `--color-text` | `#222` | |
| `--color-text-strong` | `#333` | активна стъпка (фон) |
| `--color-text-muted` | `#555` | |
| `--color-text-secondary` | `#666` | |
| `--color-disabled` | `#999` | |
| `--color-page` | `#fafafa` | **трябва да е hex** (виж 5.6) |
| `--color-surface` | `#fff` | |
| `--color-surface-muted` | `#f5f5f5` | |
| `--color-on-dark` | `#fff` | |
| `--color-border` | `#ccc` | |
| `--color-border-subtle` | `#eee` | |
| `--color-accent` | `#2980b9` | **трябва да е hex** (виж 5.6) |
| `--color-danger` | `#c0392b` | значка на стъпка |
| `--color-error` | `red` | текст на грешка |
| `--color-warning-text` | `#8a5a00` | |
| `--color-warning-bg` | `#fff7e0` | |
| `--color-warning-border` | `#e0a800` | |

Токените се четат с `var(--…)` във всички останали файлове. Нови токени (напр. `--font-display`, `--shadow-1`,
`--color-surface-raised`) се добавят САМО в `tokens.css` (тест: само `tokens.css` дефинира `--*`, и всяко `var(--x)`
трябва да е дефинирано там).

Много размери в другите файлове са буквални (1/2/3/6/10 px, размери на шрифт, ширини, 44 px, `max-height: 300/400px` на
списъците): те НЕ са токени и дизайнерът може да ги превърне в токени или да ги сменя.

### 4.3 Тема и тъмен режим

`tokens.css` е подготвен за темиране: коментарът препоръчва да се презапишат токените на `:root[data-theme="..."]`.
**Нищо още не поставя `data-theme`** (grep в `frontend/src`: няма) и няма `prefers-color-scheme` правила. Ако дизайнът
иска тъмна/светла/друга тема: (а) блоковете `:root[data-theme="dark"] { --color-...: ... }` (и/или
`@media (prefers-color-scheme: dark)`) отиват в `tokens.css` (тестът не позволява `--*` дефиниции в други файлове);
(б) за ръчен превключвател трябва малък код, който записва `data-theme` на `document.documentElement` и пази избора в
`localStorage` (нов компонент в `components/`, текстове в `copy/bg.ts` и `en.ts`, и повторно заснемане на snapshot,
защото хедърът се променя); (в) `theme-color` в `index.html` и в манифеста са статични (виж 5.6).

### 4.4 Конвенции

- Стилизиране само с **класове и data атрибути**. **Без inline стилове**: тест `frontend/src/styles.test.ts` проваля
  всеки `style={{` в `.tsx`.
- Всеки клас, който се ползва в `className="..."` на TSX, трябва да съществува в някой CSS файл (`styles.test.ts`).
  Нов клас без стил се записва като празно правило в `hooks.css`.
- Не се създават нови CSS файлове в `frontend/src/styles/` без да се добавят в `index.css` (тестът изисква всеки файл
  там да е внесен, а `tokens` да е първи).
- **Докосване:** всички бутони, линкове-бутони, входове, `summary`, редове на избирачите и етикети на чекбоксове имат
  минимум **44 px** (`min-height`/`min-width` в `touch.css`); входовете са 16 px (иначе iOS Safari приближава при
  фокус). Тези минимуми са функционални, вж. коментара в началото на `touch.css`: пази ги, визуалният размер може да е
  по-малък само ако зоната за докосване остава 44 px (padding).
- Безопасни зони: `step-nav` и `main` ползват `env(safe-area-inset-*)` (`viewport-fit=cover` в `index.html`).
- Няма hover-само функции: на iOS няма hover.
- Редът на разработка: токени → база → един компонент на ред; смени вида на страница само през CSS, после провери в
  браузъра.

### 4.5 Къде отиват шрифтове и изображения (и как се кешират офлайн)

Шрифтове за уеб (за интерфейса) са независими от PDF: PDF изнасянето ползва **DejaVu Sans** от
`server/assets/fonts/` (`DejaVuSans.ttf`, `DejaVuSans-Bold.ttf`), пакетирани в `fonts.zip` на офлайн пакета. Смяната на
уеб шрифта НЕ променя PDF.

Механизмът на офлайн кеша (`frontend/pwa/precache.mjs`, вече готов): при офлайн билд плъгинът записва `dist/sw.js` със
списък на **всеки файл от `dist/`** (освен `sw.js`, `404.html`, `*.map`, `.DS_Store`) с хеш на съдържанието. Следователно:

1. **Файл, който е в `dist/`, се кешира автоматично.** Няма ръчен списък за поддръжка.
2. Два надеждни места за шрифт/картинка:
   - **Препоръчано: `frontend/src/assets/<файл>`** (папката още не съществува, създава се) и в `@font-face` (най-добре в
     `base.css`) `src: url("../assets/<файл>.woff2")`: Vite го хешира, връзва към `base` пътя
     (`/dnd-character-creator/assets/...`) и го слага в `dist/assets/`. Работи и под под-пътя, и в Flask режим.
   - **`frontend/public/<папка>/<файл>`** (напр. `frontend/public/fonts/`): копира се както е в `dist/`, но абсолютен URL
     в CSS би пропуснал под-пътя `/dnd-character-creator/`, затова го ползвай само за файлове, които HTML/манифестът
     сочат относително (както иконите).
3. Формат: `.woff2`, с `font-display: swap`; само нужните начертания и подмножества (кирилица + латиница; обхват
   `U+0400-04FF` и `U+0000-00FF`), защото всеки килобайт увеличава първото изтегляне.
4. След добавяне: `cd frontend && VITE_BASE=/dnd-character-creator/ VITE_SERVERLESS=1 npm run build:offline` и
   `REQUIRE_PRECACHE=1 npx vitest run src/offline/precache.dist.test.mjs` (тестът проверява, че `dist/sw.js` изброява
   всеки файл с вярния хеш). Нужен е готов пакет (`scripts/build_offline.py`, раздел 7).
5. Иконите на PWA са **временни**: `frontend/public/icons/icon-192.png`, `icon-512.png`, `icon-maskable-192.png`,
   `icon-maskable-512.png`, `apple-touch-icon.png` (180x180, непрозрачна). Дизайнерът ги заменя със същите имена и
   размери; `scripts/make_pwa_icons.py` е само генератор на временните. `frontend/public/manifest.webmanifest`
   (име "Създаване на герои", кратко "Герои") и `frontend/index.html` (мета тагове) са другите файлове за иконата и
   цвета на приложението.
6. Общият размер на пакета е около 18,3 MB (23 файла) и расте с всеки шрифт/картинка; няма твърд лимит в кода (не се
   ползва Workbox), но първото изтегляне и квотата на iOS са реалното ограничение. Дръж добавените ресурси малки
   (десетки килобайти, не мегабайти) и ги измервай (`[pwa] sw.js: N files, X MB precached` при билда).

## 5. Твърди ограничения и пазачи (guards)

### 5.1 Текстове: пазачите на каталога (`frontend/src/copyGuards.test.ts`)

- **Всеки видим текст идва от `frontend/src/copy/bg.ts` и `en.ts`.** Тестът обхожда AST на изходния код: **никакви
  букви в JSX** (JSX текст, изрази-низове, `aria-label`, `title`, `placeholder`, `alt` и т.н.). Нов текст = нов ключ и в
  двата файла (`en.ts` е типизиран като `Copy`, липсващ ключ чупи `npm run build`).
- `bg` и `en` имат едни и същи ключове, една и съща аритмия на шаблоните и едни и същи параметри.
- `en.ts` **няма кирилица**. Затова етикетите на превключвателя са "BG" и "EN".
- **Latin allowlist в `bg.ts`**: латински думи в българския текст са позволени само от списък (абревиатури като AC, DC,
  PDF, YAML, STR/DEX/CON/INT/WIS/CHA; "легаси" английски думи; термини в скоби, напр. `Талант (Feat)`, от
  `BRACKET_TERMS` в същия файл, който се сверява със `server/i18n/bracket_terms.py`). Нова латинска дума в български
  текст, която не е в списъка, чупи теста.
- Правилните термини идват от речника (`frontend/src/copy/glossary.gen.ts`, генериран от `server/i18n/glossary.json`;
  вж. `docs/GLOSSARY.md`). Не измисляй нови термини; не променяй преводи без собственика (`docs/I18N-SHEET.csv` е
  защитена от дрейф: след промяна на текстове се регенерира с
  `cd server && ../.venv/bin/python -m i18n.review_sheet --csv-only`).
- Емотикони като `🎲` на бутона за случайно име са текст в каталога (`home.randomNameIcon`). Икони като SVG с `aria-hidden`
  и `role=img` са позволени като разметка, но самият достъпен текст е само от каталога.

### 5.2 Стилове (`frontend/src/styles.test.ts`)

Виж 4.4: без inline стилове, всеки клас съществува в CSS, `index.css` само `@import`, `tokens` първи, `--*` само в
`tokens.css`, правилото 44 px на `.lang-switch button`.

### 5.3 Snapshot тестове на разметката (`frontend/src/bgRender.test.ts`)

`frontend/src/__snapshots__/bg-render.json.gz` е заснет HTML на всичките маршрути в много състояния (български).
**Чист CSS не го променя.** Всяка умишлена промяна на разметката (нов елемент, клас, атрибут, ред) го чупи. Тогава:

1. направи промяната; 2. `cd frontend && UPDATE_BG_RENDER=1 npx vitest run src/bgRender.test.ts` (презаписва файла);
3. **докажи**, че промяната е точно умишлената: сравни стария и новия snapshot (напр. скрипт, който маха добавения
елемент от всички нови стойности и проверява, че старо == ново за всички ключове; така е правено за бутона "Напред");
4. опиши в доклада кои ключове се променят и защо; 5. включи обновения файл в същия commit.
Не пускай `UPDATE_BG_RENDER=1` "за да мине" без доказателство.

Други тестове на разметка: `frontend/src/components/NextStepButton.test.ts`, `frontend/src/LanguageSwitch.test.ts`,
`frontend/src/randomNameButton.test.ts`, `frontend/src/pwa/manifest.test.ts` (проверяват конкретни класове/атрибути:
не ги преименувай без да обновиш теста умишлено).

### 5.4 Команди, които трябва да минават

```
cd frontend && npm run build && npm test        # tsc + vite build, после vitest (всичко)
cd frontend && npm run test:offline             # офлайн еквивалентност (Node; пропуска се, ако няма пакет)
.venv/bin/python -m pytest -q                   # тестове в корена (около 2 s)
cd server && ../.venv/bin/python -m pytest -q   # сървърните тестове (дълги; около 2 мин, -n auto е по-бързо)
```

Някои **сървърни тестове четат изходния код на frontend-а**: `server/tests/test_types_drift.py` (чете
`frontend/src/types.ts`), `server/tests/test_t1_brackets.py` (чете `frontend/src/copyGuards.test.ts`),
`server/tests/test_i18n_completeness.py` (чете `glossary.gen.ts`), `tests/test_ci_workflow.py` (пази workflow файловете и
какво е в git). Затова: не местѝ/преименувай тези файлове и не пипай блока `BRACKET_TERMS_START ... END`.

### 5.5 iOS Safari и мобилни ограничения

- Работна ширина **375 px**; без хоризонтален скрол на страницата (широките таблици скролират в себе си).
- Без функции само при hover; всичко достъпно с докосване. Минимум 44 px цел.
- Безопасни зони (notch, home indicator) и `100dvh`; клавиатурата на iOS застъпва долната част на екрана: полетата не
  трябва да остават скрити зад нея, а долният "Напред" не трябва да е `position: fixed`, който застъпва съдържание.
- Входове с `font-size` под 16 px приближават страницата при фокус: не ги намалявай.
- **Lockdown Mode** изключва WebAssembly: приложението показва `engine-unavailable` банер; дизайнът му трябва да е ясен.
- Няма `:hover` зависимости; `:focus-visible` контурът трябва да остане видим (достъпност и клавиатура на десктоп).
- Дълги списъци: `overscroll-behavior: contain` е вече зададено; `max-height` на списъците (300/400 px) може да се
  преосмисли, но списъкът с хиляди опции не трябва да става по-бавен (не рисувай всички групи отворени).

### 5.6 Цветове на приложението извън CSS

`frontend/src/pwa/manifest.test.ts` изисква: `theme_color` и `background_color` в
`frontend/public/manifest.webmanifest` да са равни на `--color-accent` и `--color-page` от `tokens.css` (hex), и
`<meta name="theme-color">` в `frontend/index.html` да е същият като `theme_color`. Смениш ли тези два токена, смени и
трите места в същия commit. Иконите на PWA също носят цвета (`scripts/make_pwa_icons.py` чете `--color-accent`).

### 5.7 Достъпност, която вече е вградена (не я счупвай)

- При смяна на маршрут фокусът отива на `h1` (или `main`): `frontend/src/components/RouteA11y.tsx`; затова всяка страница
  има един `h1` и той трябва да се вижда/да има видим фокус. Заглавието на документа (`document.title`) се сменя по маршрут.
- `aria-label` на значките на стъпките ("неизбрани: N"), на точката "!" , на бутона "Напред" ("Напред: <стъпка>"),
  на полетата за филтър, на стъпалото за точки (намали/увеличи).
- Превключвателят на езика: `role="group"` с `aria-label`, бутони с `aria-pressed` и `lang` на всеки.
- `aria-expanded` на картите и на групите в дългия избирач; `role=tablist/tab` с `aria-selected` в Class;
  `role=alert`/`role=status` на банерите; `aria-describedby` към причината, когато опция е недостъпна.
- Контраст: поддържай WCAG AA (4.5:1 за текст); не предавай състояние само с цвят (има и "!" точка, текст "ново", причини).

### 5.8 Печат и PDF

- Печат от браузъра: виж 3.6 (`print.css`). Ако дизайнът добавя нови елементи на хрома (тема, декор), добави ги в
  списъка за скриване. Листът трябва да е четим на бяло, без тъмен фон.
- PDF/Markdown/YAML изнасянето е на сървъра/енджина (`server/export_*.py`, шаблон с DejaVu): **извън обхвата на дизайна**.

## 6. Какво НЕ се променя

- **API и форми на данните:** `docs/API.md`, `frontend/src/types.ts`, `server/service.py`, формата на черновата
  (`DRAFT_VERSION`, `frontend/src/logic/draft.ts`, `migrations.ts`). Без нови полета, без преименувания.
- **Енджинът и данните:** `server/`, `chargen/`, `scripts/build_offline.py`, пакета `frontend/public/pyodide/`.
- **Замръзени тестове и baseline файлове:** `server/tests/*baseline*.json`, golden файловете, `server/tests/export_baseline.json`,
  `service_baseline.json`. Не ги рестартирай, не ги пренареждай.
- **Каталозите за превод (i18n):** `server/i18n/*`, `docs/GLOSSARY.md`, `frontend/src/copy/glossary.gen.ts`. Позволено е
  само **добавяне на нови интерфейсни текстове** в `frontend/src/copy/bg.ts` и `en.ts` (в двата), със спазени пазачи.
- **Логиката на фронтенда:** `frontend/src/logic/*`, контекстите, `api/*`, `engine.worker.ts`, `pwa/register.ts`,
  `pwa/sw.template.js`, `pwa/precache.mjs`. Дизайнът не се нуждае от тях.
- **Работните файлове на собственика:** `Resurses/` и временните `docs/~$*`: не ги докосвай, не ги комитвай.
- Имената и значенията на `data-status`, `data-state`, `data-new`, `data-next`, `data-section`, `data-active`,
  `data-page`: тестове и бъдещ код разчитат на тях. Може да ДОБАВЯШ нови, не да преименуваш.

## 7. Как се пуска, тества, строи и публикува

Предпоставки (еднократно): `python3 -m venv .venv && .venv/bin/pip install -r server/requirements.txt`, после
`cd frontend && npm install` (или `scripts/setup.sh`). Node 22.

### 7.1 Разработка

```
cd <repo>/frontend && npm run dev            # Vite на http://localhost:5173 (изисква Flask за /api, виж по-долу)
cd <repo>/server && ../.venv/bin/python app.py    # Flask API на 127.0.0.1:8000 (Vite проксира /api към него)
cd <repo>/frontend && npm run dev:lan        # Vite достъпен от телефона по LAN IP
```

Вариант БЕЗ сървър, какъвто е и в продукцията (енджинът в браузъра): първо пакетът, после офлайн режимът.

```
cd <repo> && .venv/bin/python scripts/build_offline.py        # пакет в frontend/public/pyodide/ (около 18 MB, gitignored)
cd <repo>/frontend && npm run dev:offline                      # vite --mode offline (VITE_OFFLINE_ENGINE=1, .env.offline)
```

Конфигурация за Claude Code: `<repo>/.claude/launch.json` има `frontend-dev` (порт 5173) и `backend` (порт 8000).
Service worker не работи в браузърния панел на Claude (Electron); проверката на PWA е само в истински Chrome/Safari.

### 7.2 Билд, тестове, предварителен преглед

```
cd <repo>/frontend && npm run build           # tsc -b && vite build (Flask режим)
cd <repo>/frontend && npm test                # vitest run (всички)
cd <repo>/frontend && npm run test:offline    # само src/offline
cd <repo>/frontend && npm run typecheck       # tsc --noEmit
cd <repo> && .venv/bin/python -m pytest -q    # корен тестове
```

Билд като в продукцията (под-път + PWA) и локален преглед:

```
cd <repo> && .venv/bin/python scripts/build_offline.py
cd <repo>/frontend
VITE_BASE=/dnd-character-creator/ VITE_SERVERLESS=1 npm run build:offline
npx vite preview --base /dnd-character-creator/ --port 4180
# http://localhost:4180/dnd-character-creator/   (спри сървъра след проверката)
```

### 7.3 Публикуване

Push към `main` пуска `.github/workflows/pages.yml` (билд на пакета, `build:offline`, проверка на precache, деплой на
`frontend/dist`); сайтът е готов след 3-5 минути на https://yoanpetroshan.github.io/dnd-character-creator/. Подробности и
отстраняване на проблеми: `docs/DEPLOY-PAGES.md`. **Не пушвай без изричен ред на собственика**; първо пусни целия
набор от тестове локално. Приятелите виждат нова версия чрез банера "Има нова версия" (`update-available`) и бутон
"Обнови сега".

### 7.4 Визуална проверка (задължителна за дизайнера)

1. **Панелът на браузъра на Claude (Browser pane)**: `preview_start` с `frontend-dev` (и `backend`, или офлайн режим), после
   `resize_window` с `preset: "mobile"` (375x812) и екранни снимки на всяка страница в състоянията й (празно, чакащи
   избори, грешка, дълъг избирач, лист на герой от пример). Сложи тъмна/светла схема със `colorScheme`, ако има тема.
   Върни към `preset: "desktop"` накрая. Mobile пресетът се държи като телефон по user agent, презареди страницата.
2. **Реален iPhone през живия сайт**: след деплой отвори https://yoanpetroshan.github.io/dnd-character-creator/ в Safari,
   "Add to Home Screen", провери шрифтове, safe areas, клавиатурата, жестовете и офлайн (самолетен режим).
   Локален преглед от телефона: `npm run dev:lan` и `http://<LAN IP на Mac>:5173/`.
3. Примерен герой: създай го през интерфейса (напр. Wizard ниво 20 за най-дълъг лист и най-много заклинания, Fighter 4
   за кратък). Файловете в `frontend/src/__fixtures__/` (`wizard20-2024.json`, `fighter4-2024.json`...) са данни за
   тестове (готови резултати на енджина), а НЕ се качват от Home.
4. Преди да приключиш: `npm run build && npm test` зелено, снимки на 375 px и на 1280 px на всички 9 маршрута.

## 8. Възможности за дизайн

Кои места са естествено интересни (споменати от собственика или подсказани от кода):

- **Идентичност:** име, лого/знак за хедъра, икони на приложението (заместват временния шестоъгълник), заглавия `h1`/`h2`,
  фонови текстури. Темата е D&D: пергамент, мастило, гравюра, карти и карти на подземия, руни, но без клише и без
  копиране на търговски стил.
- **Дълги избирачи** (заклинания, умения, черти, предмети; `LongPicker`): акордеон по групи, ясен блок "Избрано",
  намиране с търсене, видим брояч, ясна разлика между избрано / налично / недостъпно (с причина) / скрито от филтрите.
  Най-много време на потребителя минава тук.
- **Списъци с ресурси** (`ClassResourcesList`, `SheetTraitsSummary`, секция `resources`): Rage, Ki, Channel Divinity
  и пр. като броячи/кръгчета/пулове.
- **Таблици на заклинанията** (`SpellSlotsSummary`, `SpellLibrary`, секции `spells`/`innateSpells`): слотове по ниво като
  последователност от символи; карта на заклинание (ниво, школа, време, обхват, компоненти, описание).
- **Листът като лист на герой:** 23-те секции са готов материал за оформление като истински лист: колони на десктоп,
  една колона на телефон, голям блок за характеристики, щитове за AC/HP/Initiative, лента с умения, рамки. Секциите са
  независими блокове с `data-section`, така че могат да се подреждат с CSS grid (`display: contents`/`grid-area` по
  `data-section`) без промяна на разметката.
- **Лентата със стъпки** и бутонът "Напред": пътуване, напредък, значки на непотвърдени неща; хоризонтален скрол на
  телефон (активната стъпка се скролира във видимата част).
- **Карти с избори:** `pending` (има какво да се направи), `new` (след level-up), `resolved`, `unavailable`, оптимален.
- **Банери:** различим език за `error`/`alert`, `notice`, офлайн готовност, обновяване.
- **Тъмен режим и теми:** куката `:root[data-theme="..."]` в `tokens.css` (4.3) + `prefers-color-scheme`; възможен
  превключвател в хедъра (изисква малък компонент и snapshot).
- **Типография:** един или два уеб шрифта (заглавия и текст) с кирилица и латиница; обмисли таблични цифри за
  модификатори (+3, -1); дисплеен шрифт за заглавия; ясно разграничаване на български текст и английски термин в скоби.
- **Движение:** леки преходи при отваряне на карта/група; зачитай `prefers-reduced-motion`.
- **Празни и зареждащи състояния:** "Loading…", празен клас/раса/произход, празна библиотека на героите.
- **Печат:** печатен вид на листа (`print.css`), който прилича на хартиен лист.

## 9. Речник на D&D термините в интерфейса

Накратко за дизайнер, който не познава D&D. Пълният речник (BG/EN, с източници) е в `docs/GLOSSARY.md`.

| Термин (в интерфейса) | Какво е |
| --- | --- |
| Character (герой) | персонажът, който играчът води; едно приложение, много герои |
| Class (Клас) | професията: Fighter (боец), Wizard (магьосник), Rogue (разбойник)... Определя умения и заклинания |
| Subclass (подклас) | специализация в класа, избира се на определено ниво |
| Level (ниво) | степен на развитие, 1 до 20; "вдигане на ниво" дава нови умения и избори |
| Species (Раса) | произходът по вид: Human, Elf, Dwarf... (в 2014 правилата се казва Race) |
| Background (Произход) | миналото на героя: Soldier, Acolyte...; дава умения, езици и черта |
| Ability Scores (Характеристики) | шест числа: STR (сила), DEX (ловкост), CON (телосложение), INT (интелект), WIS (мъдрост), CHA (харизма) |
| Ability Modifier (модификатор) | бонус/минус, изведен от характеристиката (напр. 16 дава +3); показва се със знак |
| Standard Array | готов набор от шест стойности (15, 14, 13, 12, 10, 8) |
| Point Buy | купуване на стойности с бюджет от точки |
| Roll (4d6, drop lowest) | хвърляне на четири зара, най-ниският се маха |
| Proficiency Bonus (Бонус за владеене) | бонус, който расте с нивото; добавя се към неща, в които героят е добър |
| Proficiency (владеене) | героят е обучен в умение, оръжие, броня, инструмент или спасяване |
| Expertise (експертиза) | удвоен бонус за владеене в умение |
| Skills (Умения) | 18 умения (Athletics, Stealth, Perception...), всяко е свързано с характеристика |
| Saving Throws (Спасителни хвърляния) | хвърляне за избягване на опасност (магия, капан); по едно за всяка характеристика |
| Armor Class, AC (Клас броня) | колко трудно е да бъде улучен героят; число |
| Hit Points, HP (Точки живот) | здраве; на нула героят пада |
| Hit Dice (Зарове за точки живот) | зарове, с които героят се лекува при почивка и които се хвърлят при ниво |
| Initiative (Инициатива) | число, което определя реда на ходовете в битка |
| Speed (Скорост) | колко стъпки (feet) изминава героят на ход |
| Passive Perception (Пасивно възприятие) | постоянно число за забелязване без хвърляне |
| Senses (сетива) | Darkvision, Blindsight...: способност за виждане в тъмното и др. |
| Feat (Талант) | допълнителна способност, избира се вместо подобрение на характеристика; идва и от произхода |
| Ability Score Improvement (ASI) | на определени нива: +2 характеристики или черта |
| Feature / Class Features (умение на клас) | способности, които класът дава; често с ресурс (Rage, Second Wind) |
| Resource (ресурс) | ограничен брой употреби на способност, възстановява се при почивка |
| Short Rest / Long Rest (кратка / дълга почивка) | прекъсване на играта, при което се възстановяват HP и ресурси |
| Spell (заклинание) | магия; има ниво 1 до 9, школа, време на изричане, обхват, компоненти |
| Cantrip (Трик) | заклинание от ниво 0, може да се прави неограничено |
| Spell Slots | "батерии" за заклинания: по броя на слотовете на ниво |
| Prepared Spells (Подготвени заклинания) | заклинанията, които героят е избрал за деня (за някои класове) |
| Spell Save DC | трудност на съпротивата срещу заклинанията на героя |
| Spell Attack Modifier | бонус за атака със заклинание |
| Spellbook (Книга със заклинания) | книгата на магьосника, от която подготвя заклинания |
| Pact Magic / Pact slots | магията на Warlock: малко слотове, възстановяват се при кратка почивка |
| Equipment (Екипировка) | оръжия, броня, инструменти, предмети; начална екипировка идва от класа и произхода |
| Weapon Mastery (Оръжейно майсторство) | свойство на оръжията в 2024 правилата за някои класове |
| Carrying Capacity (Товароносимост) | колко тежест носи героят (фунтове/килограми) |
| Resistance / Immunity / Vulnerability | по-малко / никакви / двойни щети от даден вид |
| Languages (Езици) | езици, на които героят говори |
| Ruleset (правила) | 2014 или 2024 издание на правилата; "Mixed" показва и двете |
| Sources (източници) | книги (PHB, XGE...), чието съдържание се показва |

Допълнителни термини, които се срещат като етикети: **Rage**, **Ki**, **Sneak Attack**, **Channel Divinity**,
**Wild Shape**, **Bardic Inspiration** (ресурси/умения на конкретни класове; идват от данните и остават на английски),
**Multiclass** (няколко класа в един герой, в Class има "добави клас"), **Darkvision**, **Subspecies/Variant**
(подраса или вариант на расата).
