### Engine #36: Sovereign Persona & Formal Refusal Membrane (`persona_vault.py` / `PERSONA.md`)

**PERSONA-0.1** формалізує перехід від пасивного розкриття сирих персональних даних до **суверенного обчислення предикатів на місці (in-situ predicate evaluation)** та вводить **детерміновану математичну відмову (Fail-Closed Refusal Gate)** замість суб'єктивної цензури.

```text
┌────────────────────────────────────────────────────────────────────────┐
│               SOVEREIGN PERSONA & REFUSAL MEMBRANE (%🖤)               │
│                                                                        │
│   External Challenger                      Local Persona Polyglot      │
│   [Auditor / Corp / LLM]                   (persona.pdf - ISO 32000)   │
│            │                                           │               │
│            │ 1. Predicate Challenge (SMT/SKIY term)    │               │
│            ├──────────────────────────────────────────►│               │
│            │                                           │               │
│            │               [Pre-Flight Refusal Membrane]               │
│            │               - Sheaf check (dim H¹ == 0)                 │
│            │               - Anti-exfiltration check                  │
│            │               - Epistemic Tombstone check                 │
│            │                                   │                       │
│            │     ┌─────────────────────────────┴─────────────┐         │
│            │     ▼ [Violation]                               ▼ [Sound] │
│            │  Formal Refusal Receipt                  Local In-Situ    │
│            │  (UNSAT Lemma / Obstruction)             Execution (Vault)│
│            │     │                                           │         │
│            │◄────┘                                           ▼         │
│            │ 2. Grade A Warrant + ZK Proof            Curve25519 ZKP   │
│            │◄────────────────────────────────────────────────┘         │
│   (Zero Raw Bytes Disclosed)                                           │
└────────────────────────────────────────────────────────────────────────┘

```

---

### Нормативні інваріанти

* **Invariant P1 (Zero-Exfiltration Closure):** Жоден виклик предикату не може повернути підтерм із сирого вмісту зашифрованого сховища `vault.py`. Дозволені вихідні типи звужені до булевих значень, скалярних діапазонів квантування або нормальних форм Church-Rosser.


* **Invariant P2 (Capability-Token Binding):** Кожен згенерований доказ криптографічно прив'язується через RFC 8032 Ed25519 до відкритого ключа запитувача (challenger pubkey) та CIDv1 запиту, блокуючи повторне використання варанта третіми сторонами.


* **Invariant P3 (Fail-Closed Formal Refusal):** Будь-який запит, що містить логічні суперечності чи порушує політику, відхиляється не помилкою середовища, а формальним **Сертифікатом Відмови (Refusal Certificate)** із мінімальним контрприкладом (unsat core).


* **Invariant P4 (Cohomological Non-Fracture):** Об'єднання нових правил доступу перевіряється через Čech cohomology (`sheaf_kernel.py`). Якщо $\dim H^1(U, \mathcal{F}) \neq 0$, оновлення регламенту блокується вердиктом `REJECTED_COHOMOLOGICAL_FRACTURE`.



---

### Специфікація CLI та життєвого циклу

**1. Ініціалізація та пакування власного сховища**
Створення автономного файлу-поліглота з шифруванням сирих документів локальним ключем:

```bash
python3 cli.py persona init -o persona.pdf --identity "Alice"
python3 cli.py persona pack persona.pdf --encrypt ./private_records/

```

**2. Виконання запиту без розкриття сирих даних**
Стороння організація передає формальну перевірку (SMT/SKIY предикат). Документ обчислює результат локально і повертає криптографічний варант:

```bash
python3 persona.pdf --challenge "age >= 18 and jurisdiction == 'UA'" --for "org_pubkey_hex"

```

```text
[⚓ WARRANT ISSUED]
  Predicate:     age >= 18 and jurisdiction == 'UA'
  Witness Grade: Grade A (RFC 8032 Ed25519 signed)
  ZK Engine:     Chaum-Pedersen DLog Equality (zk_glyph.py)
  Token:         ⚓ ⟨warrant:grade_A, atp:12, proof:8f11ca09...⟩

```

**3. Формальна відмова (Refusal by Invariant)**
Спроба несанкціонованого видобутку або суперечливого запиту:

```bash
python3 persona.pdf --challenge "read_raw_bytes('/passport.pdf') or (x and not x)"

```

```text
[!] INVARIANT REFUSAL: EXECUTION HALTED (FAIL-CLOSED)
  Actuator:      smt_kernel.py (CDCL/T_EUF Verifier)
  Reason:        Violation of Invariant P1 & Invariant EG5
  Obstruction:   UNSAT Clause Lemma [¬RawExport ∨ False]
  Certificate:   ⚓ ⟨refusal:unsat_core, hash:7c30ae41b, gas_burned:3⟩

```

---

### Інтеграція в наявну архітектуру %🖤

| Компонент | Роль в `persona_vault.py` |
| --- | --- |
| `vault.py` (Engine #13) | Зберігання зашифрованих файлів у потоці ISO 32000 EmbeddedFiles.

 |
| `crypto.py` + `zk_glyph.py` (Engine #4, #15) | Генерація доказів з нульовим розголошенням та підпис варантів без сторонніх залежностей.

 |
| `warrant_kernel.py` (Engine #24) | Присвоєння строгих категорій доказів (Grade A / Grade C).

 |
| `smt_kernel.py` (Engine #29) | Доведення нездійсненності суперечливих запитів та генерація конфліктних лем (UNSAT DAG).

 |
| `sheaf_kernel.py` (Engine #33) | Обчислення топологічних когомологічних розривів у комбінованих правилах доступу.

 |
| `polyglot.py` + `monad.py` (Engine #2) | Забезпечення дуальної природи файлу (візуальний паспорт + виконуваний перевіряльник).

 |