# DIALECTIC-0.1: Діалектичне Відкриття та Автоматична Генерація Гіпотез

> **Статус:** ПРИЙНЯТО ТА РЕАЛІЗОВАНО (DIALECTIC-0.1) у Рушії #31: [dialectic_kernel.py](dialectic_kernel.py).  
> **Проєкт:** Project Black-Heart (%🖤).  
> **Автори:** Codex, s0fractal & Antigravity (Gemini).  
> **Дата:** 2026-09-10.  
> **Призначення:** Формальна специфікація суверенного рушія автономного дослідження меж відмов («підривника устоїв»), автоматичного синтезу найслабших передумов (Weakest Preconditions) та просування гіпотез $E \to A$ у контекстний допуск [scoped_admission.py](scoped_admission.py) без епістемічного закостеніння.

---

## 1. Преамбула: Необхідність Діалектичного Відкриття

У попередніх рушіях системи Project Black-Heart було побудовано строгий дедуктивний апарат:
- `warrant_kernel.py`: Модель свідоцтв та редукційних зв'язків ($E \to A$).
- `controlled_forgetting.py`: Контрольований вихід на пенсію та надгробки.
- `scoped_admission.py`: Контекстний допуск `admission_for(...)` та захист від витоку прав.
- `smt_kernel.py`: Першопорядковий DPLL(T) верифікатор із сертифікатами UNSAT.
- `cegis_kernel.py`: Індуктивний синтез за контрприкладами.

Однак залишався бар'єр: **хто генерує нові запити на переоцінку?** Без активного автономного суб'єкта система ризикує перетворитися на пасивний архів, де кожна історична помилка залишається мертвою точкою.

Як зазначено в концепції Кодекса (`BLACK-HEART-CONDITIONAL-REOPENING-001`):
> *«Можлива функція «підривника устоїв» стає конкретною: шукати незбіг між областю старої відмови та новими умовами, пропонувати дослід, не стираючи колективну пам’ять. Імунітет зберігає право блокувати відомий збій; дослідник отримує обмежений канал перевірки іншого випадку.»*

`DIALECTIC-0.1` втілює цю функцію у вигляді **Діалектичної Тріади (Thesis $\to$ Antithesis $\to$ Synthesis)**:
- **Теза (Thesis):** Кандидат програми або мутація $T$, запропонована організмом.
- **Антитеза (Antithesis):** Запис відмови `RefusalRecord` або семантичний контрприклад $E$.
- **Синтез (Synthesis):** Автономно обчислена мінімальна дельта умов $\Delta \text{context}$ (наприклад, метаболічний бюджет кроків $\tau^*$) та найслабша захисна передумова $P(x)$, за яких кандидат стає формально доведеною теоремою і отримує `ScopedAdmission`.

---

## 2. Архітектура Суверенного Діалектичного Ядра

```
       +-----------------------------------------------------------------------------+
       |               ЕПІСТЕМІЧНИЙ СУБСТРАТ ВІДМОВ (ScopedAdmissionRegistry)         |
       |                RefusalRecord: context, steps_executed, outcome_type          |
       +-----------------------------------------------------------------------------+
                                              |
                                              v
       +-----------------------------------------------------------------------------+
       |             1. BOUNDARY FRONTIER EXPLORER («Підривник Устоїв»)              |
       |  - Аналіз причин відмови (RESOURCE_LIMIT проти SEMANTIC_COUNTEREXAMPLE)     |
       |  - Екстраполяція мінімального розширення: \Delta context (бюджет \tau*)     |
       +-----------------------------------------------------------------------------+
                                              |
                         +--------------------+--------------------+
                         |                                         |
            [SEMANTIC_COUNTEREXAMPLE]                      [RESOURCE_LIMIT]
                         |                                         |
                         v                                         v
       +------------------------------------+    +------------------------------------+
       | 2. WEAKEST PRECONDITION SYNTHESIZER|    | 3. КОНТЕКСТНЕ РОЗШИРЕННЯ           |
       |    Синтез захисного предиката P(x):|    |    \Delta steps = \tau* - \tau_old |
       |    \forall x: P(x) => C(x) == S(x) |    |    Формування ReevaluationRequest  |
       +------------------------------------+    +------------------------------------+
                         |                                         |
                         +--------------------+--------------------+
                                              |
                                              v
       +-----------------------------------------------------------------------------+
       |                  4. ДЕДУКТИВНА SMT ВЕРИФІКАЦІЯ (Engine #29)                 |
       |  Формальне доведення коректності умови через QF_UF UNSAT Refutation DAG     |
       +-----------------------------------------------------------------------------+
                                              |
                                              v
       +-----------------------------------------------------------------------------+
       |             5. КОНТЕКСТНИЙ ДОПУСК (Scoped Admission Promotion)              |
       |  - Виконання контрольованого retest у ScopedAdmissionRegistry               |
       |  - Надання ScopedAdmission (діє ТІЛЬКИ для перевіреного контексту B)        |
       +-----------------------------------------------------------------------------+
                                              |
                                              v
       +-----------------------------------------------------------------------------+
       |            6. ISO 32000 VECTOR POLYGLOT & LATIN-1 EMBEDDED AUDITOR          |
       |  Векторний дашборд тріади, таблиця дельти та автономний `python3 dialectic` |
       +-----------------------------------------------------------------------------+
```

---

## 3. Нормативні Інваріанти DIALECTIC-0.1

### Інваріант DIAL1: Minimal Frontier Delta (Мінімальність Граничної Дельти)
Обчислена зміна умов $\Delta \text{context}$ повинна бути мінімальним математично обґрунтованим розширенням, необхідним для завершення обчислення (хедрум $1.5\text{x} - 1.75\text{x}$ від точки зупинки). Забороняється довільне призначення необмежених ресурсів.

### Інваріант DIAL2: Strict Semantic Non-Promotability (Семантичний Імунітет)
Якщо `RefusalRecord` має тип `SEMANTIC_COUNTEREXAMPLE` (порушення порядку, незбіжність нормальних форм), Explorer зобов'язаний повернути статус `ANTITHESIS_UNYIELDING`. Жодне збільшення ресурсного бюджету не може бути використане для створення `ReevaluationRequest` без синтезу нової версії кандидата або явної авторизованої зміни політики.

### Інваріант DIAL3: Non-Trivial Precondition Soundness (Змістовність Передумов)
Синтезований предикат захисту $P(x)$ повинен бути задовільним ($P \not\equiv \bot$) і покривати непорожню підмножину цільового домену. Еквівалентність кандидата специфікації під умовою $P(x)$ повинна бути сертифікована SMT Proof DAG.

### Інваріант DIAL4: Historical Non-Erasure (Збереження Пам'яті)
Діалектичне відкриття ніколи не видаляє і не модифікує первісний `RefusalRecord`. Створений `ScopedAdmission` зберігає пряме посилання на `refusal_id`, фіксуючи історичну спадкоємність: невдача в $A$ залишається чинною для $A$, але відкриває допуск для $B$.

### Інваріант DIAL5: Bounded Attempt Quota (Дотримання Квот Дослідника)
Explorer підпорядковується суворому правилу квот `MAX_ATTEMPTS_PER_REFUSAL_FAMILY = 3`. Якщо родина відмови вичерпала ліміт спроб, пошук зупиняється зі статусом `RESOURCE_BOUNDED`.

### Інваріант DIAL6: ISO 32000 Vector Polyglot Physicality (Поліглотний Аудит)
Згенерований документ `dialectic_discovery.pdf` відповідає стандарту ISO 32000, візуалізує тріаду Теза-Антитеза-Синтез і є самовиконуваним скриптом Python (`python3 dialectic_discovery.pdf`), що валідує SHA-256 маніфесту без зовнішніх залежностей.

---

## 4. Програмний Інтерфейс (API)

```python
import scoped_admission
from scoped_admission import ScopedAdmissionRegistry, RefusalRecord, RefusalReason
import dialectic_kernel
from dialectic_kernel import (
    BoundaryExplorer, PreconditionSynthesizer,
    DialecticalOrchestrator, generate_dialectic_pdf
)

# 1. Створення реєстру та фіксація ресурсної відмови
registry = ScopedAdmissionRegistry()
refusal = RefusalRecord.create(
    candidate_digest="...",
    evaluator_digest="...",
    requirement_digest="...",
    inputs_digest="...",
    evidence_bytes=b"CUTOFF_AT_100",
    context={"budget_steps": 100},
    outcome_type=RefusalReason.RESOURCE_LIMIT,
    steps_executed=100
)
registry.register_refusal(refusal)

# 2. Запуск дослідника меж ("підривника устоїв")
orchestrator = DialecticalOrchestrator(registry)
report = orchestrator.discover_and_promote(
    refusal_id=refusal.record_id,
    candidate_bytes=candidate_bytes,
    executor_fn=my_executor
)

print(f"Status: {report.triad.status.value}")
print(f"Discovered Delta: +{report.triad.synthesis_delta.delta_steps} steps")
print(f"Scoped Admission: {report.scoped_admission.admission_id}")

# 3. Компіляція ISO 32000 поліглота
generate_dialectic_pdf(report, "dialectic_proof.pdf")
```

---

## 5. Командний Інтерфейс (CLI)

```bash
# Дослідити межу ресурсної відмови
python3 cli.py dialectic explore --refusal <refusal_id>

# Синтезувати найслабшу передумову для часткового збігу
python3 cli.py dialectic precond --candidate "K I" --spec "I"

# Скомпілювати векторний PDF поліглот діалектичного відкриття
python3 cli.py dialectic pdf --refusal <refusal_id> -o dialectic_proof.pdf

# Автономний аудит
python3 dialectic_proof.pdf
```
