// Bulgarian copy for the UI, structured by area. Only copy lives here: class / species / feat / spell /
// item names, feature names and rule texts come from the data as they are and are not translated.
// A second locale file (en.ts) must have exactly the same shape: `const en: Copy = {...}`.

export const bg = {
  appName: "Конструктор на герои",

  /** Labels of steps that the sheet slice added (the other step labels are still inline in logic/steps.ts). */
  nav: {
    sheet: "Лист",
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
    none: "—",
    feet: (n: number) => (n === 1 ? "1 фут" : `${n} фута`),
    pounds: (n: number) => `${n} lb`,
    level: (n: number) => `ниво ${n}`,
    levelOf: (n: number) => `от ниво ${n}`,
    gold: (n: number) => `${n} зл.`,
  },

  /** Abilities page: the table has base, bonus, total and modifier columns. */
  abilitiesPage: {
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
      slotsTitle: "Клетки за заклинания",
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

  exportPage: {
    sheetLink: "Виж листа на героя",
  },
};
