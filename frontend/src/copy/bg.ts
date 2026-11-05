// Bulgarian copy for the UI, structured by area. Only copy lives here: class / species / feat / spell /
// item names, feature names and rule texts come from the data as they are and are not translated.
// A second locale file (en.ts) must have exactly the same shape: `const en: Copy = {...}`.

type Msgs = Record<string, string>;

export const bg = {
  appName: "Конструктор на герои",

  /** The language control in the header: its group label and the two button labels. */
  lang: { label: "Език", bg: "БГ", en: "EN" },

  /** The step navigation. `steps` are the labels of the eight routes (several are English words on purpose: legacy wording kept as it was). */
  nav: {
    label: "Стъпки",
    steps: {
      home: "Home",
      class: "Клас",
      background: "Background",
      species: "Species",
      abilities: "Abilities",
      equipment: "Equipment",
      sheet: "Лист",
      export: "Export",
    },
    sheet: "Лист",
    unresolved: (n: number) => `неизбрани: ${n}`,
    newChoices: (n: number) => `Нови избори: ${n}`,
    nextStep: "Следваща незавършена стъпка →",
  },

  /** document.title per route: `${page} — ${appName}`; `fallback` for an unknown path. */
  titles: {
    separator: " — ",
    pages: {
      "/home": "Начало",
      "/class": "Клас",
      "/background": "Произход",
      "/species": "Раса",
      "/abilities": "Характеристики",
      "/equipment": "Екипировка",
      "/sheet": "Лист на героя",
      "/export": "Експорт",
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
    pounds: (n: number) => `${n} lb`,
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
    columns: { ability: "Характеристика", base: "Основа", bonus: "Бонус", total: "Общо", modifier: "Модификатор" },
  },

  sheet: {
    title: "Лист на героя",
    print: "Печат",
    exportLink: "Към експорта",
    loading: "Зареждане…",
    unnamed: "Безименен герой",
    incomplete: (count: number) =>
      count === 1
        ? "Листът е непълен: остава 1 неизбрана част или избор."
        : `Листът е непълен: остават ${count} неизбрани части или избори.`,
    markers: { proficient: "владее", expertise: "експертиза" },

    identity: {
      title: "Герой",
      name: "Име",
      level: "Общо ниво",
      classes: "Класове",
      species: "Раса",
      size: "Размер",
      background: "Произход",
      classLine: (name: string, level: number, subclass: string | null) =>
        `${name} ${level}${subclass ? ` (${subclass})` : ""}`,
      speciesLine: (name: string, subspecies: string | null, variant: string | null) =>
        name + (subspecies ? ` (${subspecies})` : "") + (variant ? ` - ${variant}` : ""),
    },

    abilities: {
      title: "Характеристики",
      columns: { ability: "Характеристика", base: "Основа", bonus: "Бонус", total: "Общо", modifier: "Модификатор" },
    },

    proficiencyBonus: { title: "Бонус за умение" },

    armorClass: { title: "Клас броня (AC)", stealthDisadvantage: "Недостатък при Скритост (носена броня)." },

    hitPoints: { title: "Точки живот", max: "Максимум", hitDice: "Зарове за живот" },

    initiative: { title: "Инициатива" },

    speeds: {
      title: "Скорост",
      modes: { walk: "ходене", fly: "летене", swim: "плуване", climb: "катерене", burrow: "ровене" } as Record<string, string>,
    },

    senses: {
      title: "Сетива",
      kinds: {
        darkvision: "тъмно зрение",
        blindsight: "сляпо зрение",
        tremorsense: "усещане за вибрации",
        truesight: "истинско зрение",
        devilsSight: "дяволско зрение",
      } as Record<string, string>,
    },

    passives: {
      title: "Пасивни стойности",
      perception: "Пасивно възприятие",
      insight: "Пасивна проницателност",
      investigation: "Пасивно разследване",
    },

    savingThrows: { title: "Спасителни хвърляния", columns: { ability: "Характеристика", bonus: "Бонус", mark: "Владеене" } },

    skills: {
      title: "Умения",
      columns: { skill: "Умение", bonus: "Бонус", mark: "Владеене" },
      otherExpertise: "Друга експертиза",
    },

    proficiencies: { title: "Владеене", armor: "Брони", weapons: "Оръжия", tools: "Инструменти" },

    languages: { title: "Езици" },

    attacks: {
      title: "Атаки",
      perAction: "Атаки на действие",
      columns: {
        weapon: "Оръжие",
        ability: "Характеристика",
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
      masteriesTitle: "Майсторство с оръжия",
    },

    resources: {
      title: "Ресурси",
      class: "Ресурси на класа",
      feat: "Ресурси от таланти",
      species: "Ресурси от расата",
      /** Text fragments of one resource line (see logic/resourceText.ts). */
      text: {
        unlimited: "без ограничение",
        pool: (n: number) => `пул ${n}`,
        bonus: (n: number) => `бонус ${n >= 0 ? "+" : ""}${n}`,
        dc: (n: number) => `ТС ${n}`,
        recharge: {
          long: "дълга почивка",
          short: "кратка почивка",
          "short-or-long": "кратка или дълга почивка",
          turn: "на ход",
          combat: "на битка",
          rage: "на ярост",
          other: "виж бележката",
        } as Record<string, string>,
        damageBonus: (n: number) => `щета +${n}`,
        heal: (h: string) => `лекуване ${h}`,
        maxCr: (cr: string) => `макс. CR ${cr}`,
        resistancesAllButPsychic: "съпротива: всички видове щета освен психична",
        resistances: (types: string[]) => `съпротива: ${types.join(", ")}`,
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
          n === 1 ? "1 използване се възстановява при кратка почивка" : `${n} използвания се възстановяват при кратка почивка`,
        spellSlotRegainsUse: "използване се възстановява срещу слот за заклинание",
        bonusActionRegainsOne: "бонус действие: връща 1 зар",
        onShortRest: "при кратка почивка",
        maxSlotLevel: (n: number) => `слотове до ниво ${n}`,
        slotCost: (level: string, points: number) => `слот ниво ${level} за ${points} т.`,
        damageTypesLine: (types: string) => `типове щета: ${types}`,
        knownForms: (n: number) => `известни форми: ${n}`,
        fly: "летене",
        swim: "плуване",
        metamagic: (list: string) => `метамагия: ${list}`,
        perRageOptions: (list: string) => `при всяка ярост една от опциите: ${list}`,
      },
    },

    features: { title: "Черти и способности", level: (n: number) => `ниво ${n}` },

    feats: { title: "Таланти", level: (n: number) => `ниво ${n}` },

    spells: {
      title: "Заклинания",
      slotsTitle: "Spell Slots",
      slotsShared: "общи за всички класове",
      pactTitle: "Магия на договора",
      slotLine: (level: number, count: number) => `ниво ${level}: ${count}`,
      ability: "Магическа характеристика",
      saveDC: "Спасяване за заклинание (DC)",
      attackBonus: "Бонус за атака",
      cantrips: "Трикове",
      known: "Известни/Подготвени заклинания",
      spellbook: "Книга със заклинания",
      alwaysPrepared: "Винаги подготвени заклинания",
      mysticArcanum: "Мистичен арканум",
      spellMastery: "Майсторство със заклинания",
      signatureSpells: "Запазени заклинания",
      pactOfTheTome: "Книга на сенките",
      spellLine: (name: string, level: number) => `${name} (ниво ${level})`,
    },

    innateSpells: {
      title: "Вродени заклинания",
      line: (name: string, uses: string, level: number | null) => `${name} (${uses}${level ? `, от ниво ${level}` : ""})`,
      ability: "характеристика",
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
      title: "Носимост",
      carried: "Носено",
      capacity: "Капацитет",
      pushDragLift: "Тласкане / влачене / вдигане",
      overCapacity: "Претоварен",
    },

    defenses: {
      title: "Съпротиви и имунитети",
      resistances: "Устойчивост към щета",
      immunities: "Имунитет към щета",
      vulnerabilities: "Уязвимост към щета",
      conditionImmunities: "Имунитет към състояния",
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
    seeInHome: "Виж в Home",
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
        "2014: увеличенията на характеристики идват от вида (species); увеличенията на произхода (background) се игнорират. Съдържанието от 2024 е скрито.",
      "2024":
        "2024: увеличенията идват от произхода (background); тези на вида се игнорират. Скрити са само стари (2014) произходи.",
      mixed:
        "Смесени: всичко е достъпно. Ако произходът дава собствено увеличение, това на вида не се прилага (без двойно броене).",
    } as Record<string, string>,
    sourcesSummary: (selected: number | null) =>
      selected === null ? "Източници (Sources) — всички" : `Източници (Sources) — ${selected} избрани`,
    sourcesAll: "Всички",
    sourcesSrdOnly: "Само SRD",
    preferencesTitle: "Preferences",
    hpPerLevel: "Точки живот на ниво",
    hpFixed: "Фиксирани (средна стойност)",
    hpManual: "Хвърляне на зарове (ръчно въвеждане)",
    prerequisites: "Изисквания",
    prereqFeats: "Прояви на дарби",
    prereqMulticlass: "Смяна на класове",
    resolutionTitle: "Resolution (from /api/resolve)",
    prunedTitle: "Отпаднали избори",
    clearPruned: "Изчисти отпаднали избори",
  },

  classPage: {
    title: "Клас",
    loadError: (detail: string) => `Грешка при зареждане на класовете: ${detail}`,
    hitDieLabel: (name: string, die: number) => `${name} (d${die})`,
    hitPoints: "Точки живот:",
    remove: "✕ Премахни",
    level: "Ниво",
    subclass: "Подклас",
    chooseSubclass: "— избери подклас —",
    higherLevels: "Способности на по-високи нива:",
    classResources: "Ресурси на класа",
    hpRolls: "Хвърляния за точки живот",
    levelN: (n: number) => `Ниво ${n}`,
    tabFeatures: "Способности",
    tabSpells: "Заклинания",
    noChoices: "Няма избори за този клас.",
    addClass: "+ Добави клас",
    levelCap: (max: number) => `Общото ниво е ${max} — намали ниво на клас, за да добавиш друг.`,
  },

  backgroundPage: {
    title: "Background",
    fallbackNote:
      "Няма 2024 backgrounds в избраните източници — показан е само SRD background (от 2014, без бонус към характеристики и Origin feat по правилата от 2024).",
    selectLabel: "Background",
    choose: "— избери background —",
    noChoices: "Няма избори за този background.",
    alignments: {
      "Lawful Good": "Законен добър",
      "Neutral Good": "Неутрален добър",
      "Chaotic Good": "Хаотичен добър",
      "Lawful Neutral": "Законен неутрален",
      "True Neutral": "Истински неутрален",
      "Chaotic Neutral": "Хаотичен неутрален",
      "Lawful Evil": "Законен зъл",
      "Neutral Evil": "Неутрален зъл",
      "Chaotic Evil": "Хаотичен зъл",
    } as Record<string, string>,
  },

  speciesPage: {
    title: "Species",
    searchLabel: "Търсене на species",
    searchPlaceholder: "Търсене на species…",
    subspecies: "Subspecies",
    subspeciesNone: "— none —",
    noChoices: "Няма избори за този species.",
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
      asi: "Увеличение на характеристики",
      general: "Общи черти",
      origin: "Черти за произход",
      "epic-boon": "Епични дарове",
      "feat-2014": "Черти (2014)",
      "any-school": "Всяка школа",
      school: "Школа на магията",
    } as Record<string, string>,
    cantripsGroup: "Трикове",
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
    filters: { all: "Всички избираеми", cantrips: "Трикове", level1: "1-во ниво" },
    cantrip: "Трик",
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
    title: "Export",
    /** File name of an unnamed hero (the server's export uses the same word per language). */
    fileFallback: "герой",
    problems: "Problems",
    unresolved: "Unresolved choices",
    attacks: "Attacks",
    attacksPerAction: (n: number) => `Attacks per action: ${n}`,
    attackDamage: (dice: string, type: string | null) => `${dice} ${type}`,
    attackVersatile: (dice: string) => `versatile ${dice}`,
    attackDueling: (dice: string) => `with Dueling ${dice}`,
    attackOffhand: (dice: string) => `off hand ${dice}`,
    attackRange: (range: string) => `range ${range}`,
    attackMastery: (mastery: string) => `mastery ${mastery}`,
    carrying: (carried: number, capacity: number, pushDragLift: number) =>
      `Carrying: ${carried}/${capacity} lb (push/drag/lift ${pushDragLift} lb)`,
    overCapacity: "over capacity",
    stealthDisadvantage: "armor: disadvantage on Stealth",
    pendingEquipment: (n: number) => `Не всички избори за екипировка са направени (${n}) — това не блокира експорта.`,
    ready: "Всичко е готово за експорт.",
    preparingPdf: "Подготвя се PDF… Първото подготвяне може да отнеме няколко секунди.",
    downloading: "Изтегляне…",
    download: (format: string) => `Изтегли ${format}`,
    missing: { class: "Избери клас.", species: "Избери species.", background: "Избери background." },
    sheetLink: "Виж листа на героя",
  },
};
