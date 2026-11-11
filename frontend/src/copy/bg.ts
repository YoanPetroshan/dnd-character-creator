// Bulgarian copy for the UI, structured by area. Only copy lives here: class / species / feat / spell /
// item names, feature names and rule texts come from the data as they are and are not translated.
// A second locale file (en.ts) must have exactly the same shape: `const en: Copy = {...}`.
// T1 (owner decision 2026-11-05): a Bulgarian rules term is followed by its English term in brackets, "Талант (Feat)"
// (docs/TERMS-PROPOSAL.md; the allowed terms are the BRACKET_TERMS list of copyGuards.test.ts).

import { formatWeight } from "../logic/units";

type Msgs = Record<string, string>;

export const bg = {
  appName: "Създаване на герои",

  /** The language control in the header: its group label and the two button labels. */
  lang: { label: "Език", bg: "БГ", en: "EN" },

  /** The step navigation. `steps` are the labels of the eight routes (Home, Abilities, Equipment and Export are English words on purpose: legacy wording kept as it was). */
  nav: {
    label: "Стъпки",
    steps: {
      home: "Home",
      class: "Клас",
      background: "Произход (Background)",
      species: "Раса (Species)",
      abilities: "Abilities",
      equipment: "Equipment",
      sheet: "Лист",
    },
    sheet: "Лист",
    unresolved: (n: number) => `неизбрани: ${n}`,
    newChoices: (n: number) => `Нови избори: ${n}`,
    nextStep: "Следваща незавършена стъпка →",
    nextButton: "Напред",
    help: "Помощ",
  },

  /** document.title per route: `${page} — ${appName}`; `fallback` for an unknown path. */
  titles: {
    separator: " — ",
    pages: {
      "/home": "Начало",
      "/class": "Клас",
      "/background": "Произход (Background)",
      "/species": "Раса (Species)",
      "/abilities": "Характеристики (Ability Scores)",
      "/equipment": "Екипировка",
      "/sheet": "Лист на героя",
      "/help": "Помощ и инсталиране",
    } as Record<string, string>,
    fallback: "Страницата не е намерена",
  },

  common: {
    loading: "Зареждане…",
    retry: "Опитай пак",
    remove: "Премахни",
    search: "Търсене…",
    noMatches: "Няма съвпадения.",
    hiddenByFilters: "скрит от текущите филтри",
    loadError: (detail: string) => `Грешка при зареждане: ${detail}`,
    errorLine: (detail: string) => `Грешка: ${detail}`,
    /** Locale of the dates the lists print. */
    dateLocale: "bg-BG",
    none: "—",
    feet: (n: number) => (n === 1 ? "1 фут" : `${n} фута`),
    /** A weight in pounds; the kilograms follow in brackets (logic/units.ts, owner decision 2026-11-10). */
    pounds: (n: number) => formatWeight(n, "bg"),
    level: (n: number) => `ниво ${n}`,
    levelOf: (n: number) => `от ниво ${n}`,
    gold: (n: number) => `${n} зл.`,
  },

  /** Abilities page: the table has base, bonus, total and modifier columns. */
  abilitiesPage: {
    title: "Abilities",
    methods: { standard: "Standard Array", pointbuy: "Point Buy", roll: "Roll (4d6, drop lowest)", manual: "Manual" },
    rollAll: "Roll all six scores",
    rerollNote: "Re-rolling replaces the current scores.",
    pointsRemaining: (n: number) => `Points Remaining: ${n}`,
    valueLabel: (ability: string) => `${ability}: стойност`,
    decreaseLabel: (ability: string) => `${ability}: намали`,
    increaseLabel: (ability: string) => `${ability}: увеличи`,
    columns: { ability: "Характеристика (Ability)", base: "Основа", bonus: "Бонус", total: "Общо", modifier: "Модификатор" },
  },

  sheet: {
    title: "Лист на героя",
    print: "Печат",
    tabs: {
      label: "Раздели на листа",
      actions: "Действия (Actions)",
      spells: "Заклинания (Spells)",
      inventory: "Екипировка (Inventory)",
      features: "Черти и особености (Features & Traits)",
      background: "Предистория (Background)",
      notes: "Бележки (Notes)",
    },
    summary: {
      label: "Кратка справка",
      ability: (ability: string, score: number, modifier: string) => `${ability} ${score} (${modifier})`,
      hitPoints: "Точки живот (Hit Points)",
      armorClass: "Клас броня (Armor Class, AC)",
      initiative: "Инициатива",
      speed: "Скорост",
      proficiencyBonus: "Бонус за владеене (Proficiency Bonus)",
      passivePerception: "Пасивно възприятие",
      hitDice: "Зарове за точки живот (Hit Point Dice)",
    },
    actionsTab: {
      standardActions: "Стандартни действия",
    },
    spellsTab: {
      empty: "Този герой няма заклинания.",
      level: (n: number) => (n === 0 ? "Трикове (Cantrips)" : `Ниво ${n}`),
      columns: { spell: "Заклинание", time: "Време", range: "Обхват", components: "Компоненти", duration: "Продължителност", notes: "Бележки" },
      concentration: "концентрация",
      ritual: "ритуал",
      marks: {
        known: "подготвено",
        spellbook: "Книга със заклинания",
        alwaysPrepared: "винаги подготвено",
        mysticArcanum: "мистичен арканум",
        spellMastery: "майсторство",
        signatureSpells: "запазено",
        pactOfTheTome: "книга на сенките",
      },
    },
    featuresTab: {
      filtersLabel: "Филтър",
      filters: { all: "Всички", class: "Клас", species: "Раса (Species)", feats: "Таланти (Feats)" },
      source: { class: "Клас", species: "Раса (Species)", background: "Произход (Background)" },
      empty: "Няма черти в този филтър.",
    },
    notesTab: { empty: "Няма бележки." },
    loading: "Зареждане…",
    unnamed: "Безименен герой",
    incomplete: (count: number) =>
      count === 1
        ? "Листът е непълен: остава 1 неизбрана част или избор."
        : `Листът е непълен: остават ${count} неизбрани части или избори.`,
    markers: { proficient: "владее", expertise: "експертиза (Expertise)" },

    identity: {
      title: "Герой",
      name: "Име",
      level: "Общо ниво",
      classes: "Класове",
      species: "Раса (Species)",
      size: "Размер",
      background: "Произход (Background)",
      classLine: (name: string, level: number, subclass: string | null) =>
        `${name} ${level}${subclass ? ` (${subclass})` : ""}`,
      speciesLine: (name: string, subspecies: string | null, variant: string | null) =>
        name + (subspecies ? ` (${subspecies})` : "") + (variant ? ` - ${variant}` : ""),
    },

    abilities: {
      title: "Характеристики (Ability Scores)",
      columns: { ability: "Характеристика (Ability)", base: "Основа", bonus: "Бонус", total: "Общо", modifier: "Модификатор" },
    },

    proficiencyBonus: { title: "Бонус за владеене (Proficiency Bonus)" },

    armorClass: { title: "Клас броня (Armor Class, AC)", stealthDisadvantage: "Недостатък (Disadvantage) при Скритост (носена броня)." },

    hitPoints: { title: "Точки живот (Hit Points)", max: "Максимум", hitDice: "Зарове за точки живот (Hit Point Dice)" },

    initiative: { title: "Инициатива" },

    speeds: {
      title: "Скорост",
      modes: { walk: "ходене", fly: "летене", swim: "плуване", climb: "катерене", burrow: "ровене" } as Record<string, string>,
    },

    senses: {
      title: "Сетива (Senses)",
      kinds: {
        darkvision: "тъмно зрение (Darkvision)",
        blindsight: "сляпо зрение (Blindsight)",
        tremorsense: "усещане за вибрации (Tremorsense)",
        truesight: "истинско зрение (Truesight)",
        devilsSight: "дяволско зрение (Devil's Sight)",
      } as Record<string, string>,
    },

    passives: {
      title: "Пасивни стойности",
      perception: "Пасивно възприятие",
      insight: "Пасивна проницателност",
      investigation: "Пасивно разследване",
    },

    savingThrows: { title: "Спасителни хвърляния (Saving Throws)", columns: { ability: "Характеристика (Ability)", bonus: "Бонус", mark: "Владеене (Proficiency)" } },

    skills: {
      title: "Умения (Skills)",
      columns: { skill: "Умение (Skill)", bonus: "Бонус", mark: "Владеене (Proficiency)" },
      otherExpertise: "Друга експертиза (Other Expertise)",
    },

    proficiencies: { title: "Владеене (Proficiencies)", armor: "Брони", weapons: "Оръжия", tools: "Инструменти" },

    languages: { title: "Езици" },

    attacks: {
      title: "Атаки",
      perAction: "Атаки на действие",
      columns: {
        weapon: "Оръжие",
        ability: "Характеристика (Ability)",
        bonus: "Атака",
        damage: "Щета",
        range: "Обхват",
        mastery: "Майсторство",
        notes: "Бележки",
      },
      proficient: "владее",
      wielded: "в ръка",
      damage: (dice: string, type: string | null) => (type ? `${dice} ${type}` : dice),
      versatile: (dice: string) => `двуръчно ${dice}`,
      dueling: (dice: string) => `с Дуел ${dice}`,
      offhand: (dice: string) => `в свободната ръка ${dice}`,
      masteriesTitle: "Майсторство с оръжия (Weapon Mastery)",
    },

    resources: {
      title: "Ресурси",
      class: "Ресурси на класа",
      feat: "Ресурси от таланти (Feats)",
      species: "Ресурси от расата (Species)",
      /** Text fragments of one resource line (see logic/resourceText.ts). */
      text: {
        unlimited: "без ограничение",
        pool: (n: number) => `пул ${n}`,
        bonus: (n: number) => `бонус ${n >= 0 ? "+" : ""}${n}`,
        dc: (n: number) => `ТС ${n}`,
        recharge: {
          long: "дълга почивка (Long Rest)",
          short: "кратка почивка (Short Rest)",
          "short-or-long": "кратка почивка (Short Rest) или дълга почивка (Long Rest)",
          turn: "на ход",
          combat: "на битка",
          rage: "на ярост",
          other: "виж бележката",
        } as Record<string, string>,
        damageBonus: (n: number) => `щета +${n}`,
        heal: (h: string) => `лекуване ${h}`,
        maxCr: (cr: string) => `макс. CR ${cr}`,
        resistancesAllButPsychic: "устойчивост (Resistance): всички видове щети освен психични",
        resistances: (types: string[]) => `устойчивост (Resistance): ${types.join(", ")}`,
        damageTypes: {
          acid: "киселинни",
          bludgeoning: "дробящи",
          cold: "студени",
          fire: "огнени",
          force: "силови",
          lightning: "мълниеносни",
          necrotic: "некротични",
          piercing: "пробождащи",
          poison: "отровни",
          psychic: "психични",
          radiant: "лъчисти",
          slashing: "режещи",
          thunder: "гръмотевични",
        } as Record<string, string>,
        shortRestRegains: (n: number) =>
          n === 1 ? "1 използване се възстановява при кратка почивка (Short Rest)" : `${n} използвания се възстановяват при кратка почивка (Short Rest)`,
        spellSlotRegainsUse: "използване се възстановява срещу Spell Slot",
        bonusActionRegainsOne: "бонус действие (Bonus Action): връща 1 зар",
        onShortRest: "при кратка почивка (Short Rest)",
        maxSlotLevel: (n: number) => `Spell Slots до ниво ${n}`,
        slotCost: (level: string, points: number) => `Spell Slot ниво ${level} за ${points} т.`,
        damageTypesLine: (types: string) => `типове щети: ${types}`,
        knownForms: (n: number) => `известни форми: ${n}`,
        fly: "летене",
        swim: "плуване",
        metamagic: (list: string) => `метамагия: ${list}`,
        perRageOptions: (list: string) => `при всяка ярост една от опциите: ${list}`,
      },
    },

    features: { title: "Способности на класа (Class Features)", level: (n: number) => `ниво ${n}` },

    feats: { title: "Таланти (Feats)", level: (n: number) => `ниво ${n}` },

    spells: {
      title: "Заклинания",
      slotsTitle: "Spell Slots",
      slotsShared: "общи за всички класове",
      pactTitle: "Магия на договора",
      slotLine: (level: number, count: number) => `ниво ${level}: ${count}`,
      ability: "Магическа характеристика (Spellcasting Ability)",
      saveDC: "DC на спасяването от заклинание (Spell Save DC)",
      attackBonus: "Бонус за атака със заклинание (Spell Attack Modifier)",
      cantrips: "Трикове (Cantrips)",
      known: "Известни/Подготвени заклинания",
      spellbook: "Книга със заклинания",
      alwaysPrepared: "Винаги подготвени заклинания",
      mysticArcanum: "Мистичен арканум",
      spellMastery: "Майсторство със заклинания (Spell Mastery)",
      signatureSpells: "Запазени заклинания",
      pactOfTheTome: "Книга на сенките",
      spellLine: (name: string, level: number) => `${name} (ниво ${level})`,
    },

    innateSpells: {
      title: "Вродени заклинания",
      line: (name: string, uses: string, level: number | null) => `${name} (${uses}${level ? `, от ниво ${level}` : ""})`,
      ability: "характеристика (Ability)",
      variant: "вариант",
    },

    equipment: {
      title: "Екипировка",
      groups: { granted: "Получена екипировка", chosen: "Избрана екипировка", added: "Инвентар" },
      equipped: "екипиран",
      quantity: (n: number) => `×${n}`,
      contents: "Съдържание",
      worn: "Носено",
      armor: "Броня",
      noArmor: "без броня",
      shield: "щит",
      handsTitle: "В ръце",
      mainHand: "основна ръка",
      offHand: "свободна ръка",
      emptyHand: "празна",
      startingGold: "Начално злато",
      narrativeItems: "Други предмети",
    },

    carryingCapacity: {
      title: "Носимост (Carrying Capacity)",
      carried: "Носено",
      capacity: "Капацитет",
      pushDragLift: "Тласкане / влачене / вдигане",
      overCapacity: "Претоварен",
    },

    defenses: {
      title: "Устойчивост (Resistance) и имунитети (Immunities)",
      resistances: "Устойчивост (Resistance) към щети",
      immunities: "Имунитет (Immunity) към щети",
      vulnerabilities: "Уязвимост (Vulnerability) към щети",
      conditionImmunities: "Имунитет (Immunity) към състояния",
    },

    details: {
      title: "Данни за героя",
      sections: {
        character: "Данни",
        physical: "Физически характеристики",
        personality: "Личност",
        notes: "Бележки",
      },
      fields: {
        alignment: "Мирогледие",
        faith: "Вяра/Божество",
        lifestyle: "Начин на живот",
        age: "Възраст",
        height: "Височина",
        weight: "Тегло",
        eyes: "Очи",
        skin: "Кожа",
        hair: "Коса",
        personalityTraits: "Черти на характера",
        ideals: "Идеали",
        bonds: "Връзки",
        flaws: "Слабости",
        backstory: "Предистория",
        organizations: "Организации",
        allies: "Съюзници",
        enemies: "Врагове",
        notes: "Допълнителни бележки",
      },
    },
  },

  /** App-wide status lines (StatusBanner). */
  status: {
    calcError: (detail: string) => `Грешка при изчисляване: ${detail}`,
    lastGood: "Показани са последните успешни данни.",
    downloadOld: "Свали старата чернова",
    copyText: "Копирай текста",
    dismiss: "Разбрах",
    storageFailed:
      "Черновата не може да се запази в браузъра (пълно или забранено хранилище). Изтегли я от Home като файл, за да не я загубиш.",
    pruned: (n: number) => `Отпаднали избори: ${n}.`,
    serverOlder: "Сървърът е по-стара версия от приложението и може да не разпознае всички данни на героя. Обнови сървъра.",
    engineStarting: "Стартира се двигателят на приложението… Първото стартиране може да отнеме няколко секунди.",
    engineUnavailable:
      "Двигателят на приложението не може да стартира: браузърът няма WebAssembly (на iPhone това става в режим Lockdown Mode) или файловете на приложението не са изтеглени. Отворете приложението с интернет връзка или го пуснете в друг браузър.",
    seeInHome: "Виж в Home",
  },

  /** Offline use (service worker): banner lines and the Help page. */
  pwa: {
    installing: "Приложението се изтегля за работа без връзка (около 20 MB). Не затваряйте страницата.",
    offlineReady: "Готово: приложението работи и без интернет.",
    updateAvailable: "Има нова версия на приложението.",
    updateNow: "Обнови сега",
    helpLink: "Помощ",
  },

  help: {
    title: "Помощ и инсталиране",
    offlineTitle: "Работа без връзка",
    status: {
      idle: "Тази версия на приложението не се инсталира за работа без връзка.",
      unsupported: "Този браузър не поддържа работа без връзка (липсва поддръжка на работа без връзка или страницата не е на защитен адрес). Приложението работи само докато има връзка.",
      installing: "Приложението се изтегля за работа без връзка (около 20 MB). Не затваряйте страницата.",
      "offline-ready": "Готово: приложението е запазено в браузъра и работи без интернет.",
      "update-available": "Има нова версия на приложението, изтеглена и готова за пускане.",
      error: "Не се получи запазване за работа без връзка. Презаредете страницата, докато има връзка.",
    } as Record<string, string>,
    storage: {
      granted: "Браузърът пази данните на приложението от автоматично изчистване.",
      denied: "Браузърът не гарантира данните: може да ги изчисти, ако дълго не отваряте приложението. Добавете го към началния екран и пазете копие на героите.",
    } as Record<string, string>,
    updateNow: "Обнови сега",
    installTitle: "Инсталиране на телефона",
    iosTitle: "iPhone и iPad в Safari",
    iosSteps: [
      "Отворете адреса на приложението в Safari (не във вграден браузър на друго приложение).",
      "Натиснете бутона за споделяне (квадрат със стрелка нагоре).",
      "Изберете „Добави към началния екран“ и после „Добави“.",
      "Пускайте приложението от иконата на началния екран. Първото пускане е с интернет връзка; след това работи и без нея.",
    ],
    androidTitle: "Android в Chrome",
    androidSteps: [
      "Отворете адреса на приложението в Chrome.",
      "Натиснете менюто с трите точки и изберете „Инсталиране на приложение“ (или „Добавяне към началния екран“).",
      "Пускайте приложението от иконата. Първото пускане е с интернет връзка; след това работи и без нея.",
    ],
    desktopTitle: "Компютър с Chrome или Edge",
    desktopText: "Натиснете иконата за инсталиране в адресния ред. Инсталирането не е задължително: приложението работи и в обикновен раздел.",
    keepTitle: "Пазете героите си",
    keepText:
      "Героите се пазят само в този браузър. iPhone може да изчисти данните на сайт, който не сте отваряли 7 дни, освен ако не е добавен към началния екран; смяна на телефон или изчистване на данните също ги губи. Дръжте копие във файл.",
    keepLink: "Изтегли всички герои (.json) в Home",
    lockdownTitle: "Ако не тръгва",
    lockdownText:
      "На iPhone режимът Lockdown Mode изключва WebAssembly и приложението не може да работи в него: изключете го за Safari или ползвайте друго устройство. Ако нещо се е развалило, изчистете данните на сайта в настройките на браузъра (героите се губят: първо ги изтеглете) и отворете приложението отново.",
  },

  errorBoundary: {
    title: "Нещо се обърка",
    body: (detail: string) => `Приложението се натъкна на грешка: ${detail}`,
    hint: "Можеш да запазиш чернова като файл и да започнеш наново.",
    download: "Изтегли черновата (JSON)",
    reset: "Нулирай черновата",
  },

  home: {
    title: "Home",
    nameLabel: "Character Name",
    randomName: "Случайно име",
    randomNameIcon: "🎲",
    nameHint: "Saved as you type — reload the page and this name should still be here.",
    charactersTitle: "Герои",
    unnamed: "Без име",
    active: "(активен)",
    corrupt: "повредена чернова",
    noStoredDraft: "няма запазена чернова",
    noClass: "без клас",
    itemSummary: (classes: string, total: number) => `${classes}, общо ниво ${total}`,
    updated: (when: string) => `променен ${when}`,
    open: "Отвори",
    rename: "Преименувай",
    duplicate: "Копирай",
    delete: "Изтрий",
    newHero: "Нов герой",
    downloadAll: "Изтегли всички (.json)",
    upload: "Качи герой или пакет (.json)",
    downloadOne: "Изтегли този герой (.json)",
    exportedAll: "Пакетът с всички герои е изтеглен.",
    exportedSkipped: (names: string) => `Пакетът е изтеглен без повредени герои: ${names}.`,
    renamePrompt: "Ново име на героя:",
    deleteConfirm: (name: string) => `Изтриване на героя „${name}“? Това не може да се отмени.`,
    importSummary: (added: number, rejected: number) =>
      `Качване: ${added} добавени, ${rejected} отхвърлени. Съществуващите герои не са променени.`,
    importIndex: (n: number) => `№ ${n}`,
    importAccepted: "добавен",
    importRejected: "отхвърлен",
    hide: "Скрий",
    rulesTitle: "Правила и източници",
    rulesetLabel: "Правила (ruleset)",
    rulesetMixed: "Смесени",
    rulesetHelp: {
      "2014":
        "2014: увеличенията на характеристики (Ability Scores) идват от расата (Species); увеличенията на произхода (Background) се игнорират. Съдържанието от 2024 е скрито.",
      "2024":
        "2024: увеличенията идват от произхода (Background); тези на расата (Species) се игнорират. Скрити са само стари (2014) произходи.",
      mixed:
        "Смесени: всичко е достъпно. Ако произходът (Background) дава собствено увеличение, това на расата (Species) не се прилага (без двойно броене).",
    } as Record<string, string>,
    sourcesSummary: (selected: number | null) =>
      selected === null ? "Източници (Sources) — всички" : `Източници (Sources) — ${selected} избрани`,
    sourcesAll: "Всички",
    sourcesSrdOnly: "Само SRD",
    preferencesTitle: "Preferences",
    hpPerLevel: "Точки живот (Hit Points) на ниво",
    hpFixed: "Фиксирани (средна стойност)",
    hpManual: "Хвърляне на зарове (ръчно въвеждане)",
    prerequisites: "Изисквания",
    prereqFeats: "Изисквания за таланти (Feat Prerequisites)",
    prereqMulticlass: "Смяна на класове",
    resolutionTitle: "Resolution (from /api/resolve)",
    prunedTitle: "Отпаднали избори",
    clearPruned: "Изчисти отпаднали избори",
  },

  classPage: {
    title: "Клас",
    loadError: (detail: string) => `Грешка при зареждане на класовете: ${detail}`,
    hitDieLabel: (name: string, die: number) => `${name} (d${die})`,
    hitPoints: "Точки живот (Hit Points):",
    remove: "✕ Премахни",
    level: "Ниво",
    subclass: "Подклас",
    chooseSubclass: "— избери подклас —",
    higherLevels: "Способности (Features) на по-високи нива:",
    classResources: "Ресурси на класа",
    hpRolls: "Хвърляния за точки живот (Hit Points)",
    levelN: (n: number) => `Ниво ${n}`,
    tabFeatures: "Способности (Features)",
    tabSpells: "Заклинания",
    noChoices: "Няма избори за този клас.",
    addClass: "+ Добави клас",
    levelCap: (max: number) => `Общото ниво е ${max} — намали ниво на клас, за да добавиш друг.`,
  },

  backgroundPage: {
    title: "Произход (Background)",
    fallbackNote:
      "Няма произход (Background) от 2024 в избраните източници — показан е само SRD произход от 2014, без бонус към характеристики (Ability Scores) и талант от произхода (Origin Feat) по правилата от 2024.",
    selectLabel: "Произход (Background)",
    choose: "— избери произход (Background) —",
    noChoices: "Няма избори за този произход (Background).",
    alignments: {
      "Lawful Good": "Законно добър",
      "Neutral Good": "Неутрално добър",
      "Chaotic Good": "Хаотично добър",
      "Lawful Neutral": "Законно неутрален",
      "True Neutral": "Напълно неутрален",
      "Chaotic Neutral": "Хаотично неутрален",
      "Lawful Evil": "Законно зъл",
      "Neutral Evil": "Неутрално зъл",
      "Chaotic Evil": "Хаотично зъл",
    } as Record<string, string>,
  },

  speciesPage: {
    title: "Раса (Species)",
    searchLabel: "Търсене на раса (Species)",
    searchPlaceholder: "Търсене на раса (Species)…",
    subspecies: "Subspecies",
    subspeciesNone: "— none —",
    noChoices: "Няма избори за тази раса (Species).",
  },

  equipmentPage: {
    title: "Equipment",
    categories: {
      all: "Всички",
      weapon: "Оръжия",
      armor: "Брони",
      "adventuring-gear": "Снаряжение",
      tools: "Инструменти",
      "mounts-and-vehicles": "Превозни средства",
    } as Record<string, string>,
    contains: (list: string) => `(съдържа: ${list})`,
    noStartingChoices: "Няма избори за стартова екипировка.",
    wornAndHeld: "Носено и държано",
    setWornManually: "Задай ръчно какво нося",
    armor: "Броня",
    noArmor: "Без броня",
    shield: "Щит",
    setWieldedManually: "Задай ръчно какво държа в ръцете",
    mainHand: "Основна ръка",
    offHand: "Свободна ръка",
    emptyHand: "Празна",
    itemsTitle: "Предмети",
    searchLabel: "Търсене на предмети",
    categoryLabel: "Категория",
    add: "Add",
    addLabel: (name: string) => `Добави ${name}`,
    removeLabel: (name: string) => `Премахни ${name}`,
    noAdded: "Няма добавени предмети.",
    equipped: "Екипиран",
  },

  choice: {
    newMarker: "ново",
    pendingDot: "pending choice",
    levelBadge: (level: number) => `${level} level`,
    counter: (selected: number, count: number) => `избрани ${selected}/${count}`,
    granted: (list: string) => `Получавате автоматично: ${list}`,
    groups: {
      asi: "Увеличение на характеристики (Ability Score Improvement)",
      general: "Общи таланти (General Feats)",
      origin: "Таланти от произхода (Origin Feats)",
      "epic-boon": "Епични дарове",
      "feat-2014": "Таланти от 2014 (Feats)",
      "any-school": "Всяка школа",
      school: "Школа на магията",
    } as Record<string, string>,
    cantripsGroup: "Трикове (Cantrips)",
    spellLevelGroup: (level: string) => `Заклинания ниво ${level}`,
    searchLabel: (label: string) => `Търсене: ${label}`,
    hideUnavailable: "Скриване на недостъпните",
    showUnavailable: (n: number) => `Показване на недостъпните (${n})`,
    selectedTitle: "Избрано",
    selectedCount: (selected: number, count: number) => `Избрано (${selected}/${count})`,
    removeLabel: (label: string) => `Премахни: ${label}`,
    sourceLabel: (label: string) => `Източник: ${label}`,
    allSources: "Всички източници",
    unlabelled: (n: number) => `Без етикет (${n})`,
    found: (available: number, hidden: number) =>
      `Намерени: ${available}${hidden > 0 ? ` (още ${hidden} недостъпни)` : ""}`,
    other: "Други",
    groupSummary: (available: number, hidden: number, selected: number) =>
      [`${available} налични`, ...(hidden > 0 ? [`${hidden} недостъпни`] : []), ...(selected > 0 ? [`избрани ${selected}`] : [])].join(", "),
  },

  spellLibrary: {
    title: "Списък със заклинания",
    searchLabel: "Търсене на заклинания",
    levelLabel: "Ниво на заклинанията",
    filters: { all: "Всички избираеми", cantrips: "Трикове (Cantrips)", level1: "1-во ниво" },
    cantrip: "Трик (Cantrip)",
    levelBadge: (n: number) => `${n} ниво`,
    concentration: "Концентрация",
    ritual: "Ритуал",
  },

  traits: {
    senseLine: (name: string, feet: number) => `${name} ${feet} фута`,
  },

  slots: {
    line: (level: number, count: number) => `ниво ${level} ×${count}`,
    pactLine: (count: number, level: number) => `${count} × ниво ${level}`,
  },

  /** Messages of pure modules and hooks (see logic/messages.ts); `p` holds the already rendered parameters. */
  msg: {
    raw: (p: Msgs) => p.text,
    "http.400": () => "Черновата не е във вярна форма и сървърът я отхвърли.",
    "http.413": () => "Черновата е твърде голяма за сървъра (над 1 MB).",
    "http.500": () => "Сървърът има вътрешна грешка. Опитай пак след малко.",
    "http.gateway": (p: Msgs) => `Няма връзка със сървъра (${p.status}).`,
    "http.other": (p: Msgs) => `Сървърът върна грешка ${p.status}.`,
    "http.detail": (p: Msgs) => `${p.base} Технически детайл: ${p.detail}`,
    "net.offline": () => "Няма връзка със сървъра.",
    "net.timeout": () => "Сървърът не отговори навреме.",
    "catalog.failed": (p: Msgs) => `Каталогът не се зареди (грешка ${p.status}).`,
    "items.failed": (p: Msgs) => `Списъкът не се зареди (грешка ${p.status}).`,
    "spells.failed": (p: Msgs) => `Списъкът със заклинания не се зареди (грешка ${p.status}).`,
    "spell.failed": (p: Msgs) => `Заклинанието не се зареди (грешка ${p.status}).`,
    "export.refused": (p: Msgs) => `Експортът е отказан, докато има проблеми в черновата: ${p.text}`,
    "export.failed": (p: Msgs) => `Експортът не успя. ${p.detail}`,
    "export.offline": () => "Няма връзка със сървъра. Експортът не е изтеглен.",
    "file.notJson": () => "Файлът не е валиден JSON.",
    "draft.notADraft": () => "Файлът не е чернова на герой.",
    "draft.newer": () => "Тази чернова е записана от по-нова версия на приложението.",
    "draft.notRecognised": () => "Файлът не прилича на чернова на герой.",
    "lib.unreadable": () => "Запазената чернова е повредена.",
    "lib.cannotRead": () => "Запазената чернова не може да се прочете.",
    "lib.isolated": (p: Msgs) =>
      `Героят „${p.name || "Без име"}": ${p.why} Започнат е празен; старият текст е запазен в браузъра (${p.key}).`,
    "lib.isolatedNoBackup": (p: Msgs) =>
      `Героят „${p.name || "Без име"}": ${p.why} Копие НЕ можа да се запази (хранилището е пълно); повредените данни са оставени непипнати.`,
    "lib.libraryDamaged": (p: Msgs) =>
      `Списъкът с герои (библиотеката) е повреден или от по-нова версия. ${p.saved}${p.recovered}`,
    "lib.backupSaved": (p: Msgs) => `Старият текст е запазен в браузъра (${p.key}).`,
    "lib.backupFailed": () => "Копие НЕ можа да се запази (хранилището е пълно).",
    "lib.recovered": () => " Героите са възстановени от запазените чернови.",
    "lib.startedEmptyLibrary": () => " Започнато е с празна библиотека.",
    "lib.legacyBackedUp": (p: Msgs) =>
      `${p.why} Започнато е с празна чернова; старата е запазена в браузъра (${p.key}).`,
    "lib.legacyNotBackedUp": (p: Msgs) =>
      `${p.why} Започнато е с празна чернова, а старата НЕ можа да се запази в браузъра (хранилището е пълно). Свали я сега, иначе ще се загуби.`,
    "lib.bundleNewer": () => "Пакетът с герои е записан от по-нова версия на приложението.",
    "lib.bundleNoList": () => "Пакетът с герои няма списък с чернови.",
    "lib.bundleEmpty": () => "Пакетът с герои е празен.",
    "lib.tooMany": (p: Msgs) => `Пакетът е прекалено голям: приемат се най-много ${p.max} героя.`,
    "lib.cannotStore": () => "Не можа да се запази: хранилището на браузъра е пълно или забранено.",
    "lib.added": () => "Добавен като нов герой.",
  },

  /** Words the character library stores into character names (a copy of a hero). */
  library: {
    unnamed: "Без име",
    copyName: (name: string) => `${name} (копие)`,
  },

  exportPage: {
    /** File name of an unnamed hero (the server's export uses the same word per language). */
    fileFallback: "герой",
    heading: "Изтегляне",
    problems: "Проблеми в черновата",
    unresolved: "Неизбрани избори",
    pendingEquipment: (n: number) => `Не всички избори за екипировка са направени (${n}) — това не блокира изтеглянето.`,
    ready: "Всичко е готово за изтегляне.",
    notReady: "Изтеглянето е недостъпно, докато не бъдат оправени горните неща.",
    preparingPdf: "Подготвя се PDF… Първото подготвяне може да отнеме няколко секунди.",
    downloading: "Изтегляне…",
    downloadSheet: "Лист за игра (форма)",
    downloadMarkdown: "Markdown",
    missing: { class: "Избери клас.", species: "Избери раса (Species).", background: "Избери произход (Background)." },
  },
};
