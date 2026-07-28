# Marine Engineer Exam Prep Platform — Build Spec (v1)

## 1. Purpose

A public, membership-gated web platform for MCA/SQA Chief Engineer exam preparation,
covering five subjects: **EK Motor, EK General, EK Naval, EK Electrical, EK Oral**.
Modeled on Marine Samraj (topic/year-segregated question practice), extended with
examiner-feedback highlighting, cross-diet question tracking, and user-submitted
answer improvements under admin moderation.

---

## 2. Site Map

```
Home (public)
 └─ Sign up / Log in

Home (authenticated + approved only)
 ├─ EK Motor
 │   └─ Diet list (latest diet → March 2017)
 │        └─ Diet page (all questions asked that sitting)
 │             └─ Question page
 │                  ├─ Canonical answer
 │                  ├─ Examiner Feedback (highlighted)
 │                  ├─ "Also asked in: [other diet dates]"
 │                  └─ "Suggest Improvement" button
 ├─ EK General    (same structure as EK Motor)
 ├─ EK Naval      (same structure as EK Motor)
 ├─ EK Electrical (same structure as EK Motor)
 └─ EK Oral
     └─ Flat question list (topic chips + search bar — no diet layer)
          └─ Question page
               ├─ Canonical answer
               ├─ "What Examiner Would Drill Into" (highlighted)
               └─ "Suggest Improvement" button

Admin-only (you)
 ├─ Member approval queue (approve/reject signups)
 └─ Suggested-edit moderation queue (approve/amend/reject answer suggestions)
```

---

## 3. Data Model (Postgres)

### `subjects`
| column | type | notes |
|---|---|---|
| id | serial PK | |
| name | text | "EK Motor", "EK Oral", etc. |
| slug | text unique | url-friendly |

### `diets`
| column | type | notes |
|---|---|---|
| id | serial PK | |
| subject_id | FK → subjects | |
| label | text | e.g. "July 2025" |
| date | date | |
| sort_order | int | for latest-first ordering |

Unused for EK Oral (no rows needed, or simply never referenced).

### `topics`
| column | type | notes |
|---|---|---|
| id | serial PK | |
| subject_id | FK → subjects | |
| name | text | e.g. "Fuel", "Cooling", "Governors" |

Used for filter chips in all subjects; primary browse axis for EK Oral.

### `canonical_answers`
| column | type | notes |
|---|---|---|
| id | serial PK | |
| subject_id | FK → subjects | |
| topic_id | FK → topics | |
| answer_text | text | authored once, shared across repeated instances |
| sketch_refs | jsonb / text[] | references to stored diagram images |

### `question_instances`
| column | type | notes |
|---|---|---|
| id | serial PK | |
| canonical_answer_id | FK → canonical_answers | |
| diet_id | FK → diets, **nullable** | NULL for every EK Oral row |
| question_number | text | as printed in that diet/source |
| question_text_as_asked | text | verbatim wording for that sitting |
| examiner_feedback_text | text | labeled "Examiner Feedback" (written) or "What Examiner Would Drill Into" (Oral) |

**Cross-diet lookup:** "also asked in" = all other `question_instances` sharing the
same `canonical_answer_id`, joined to their `diets.label`.

### `users`
| column | type | notes |
|---|---|---|
| id | serial PK | |
| email | text unique | |
| password_hash | text | |
| status | enum | `pending` / `approved` / `rejected` |
| is_admin | boolean | true only for your account |
| created_at | timestamp | |

### `suggested_edits`
| column | type | notes |
|---|---|---|
| id | serial PK | |
| canonical_answer_id | FK → canonical_answers | attaches to the answer, not one instance |
| submitted_by_user_id | FK → users | |
| suggested_text | text | |
| status | enum | `pending` / `approved` / `rejected` |
| submitted_at | timestamp | |
| reviewed_at | timestamp, nullable | |

### `suggested_edit_sketches`
| column | type | notes |
|---|---|---|
| id | serial PK | |
| suggested_edit_id | FK → suggested_edits | |
| image_path | text | path in object storage, not DB blob |

### `answer_history`
| column | type | notes |
|---|---|---|
| id | serial PK | |
| canonical_answer_id | FK → canonical_answers | |
| previous_text | text | |
| previous_sketch_refs | jsonb / text[] | |
| changed_at | timestamp | |

Written on every approved amendment, so changes are auditable/reversible.

---

## 4. Core Flows

### 4.1 Signup / Approval Gate
1. Visitor signs up → `users` row created, `status = 'pending'`.
2. Visitor sees a "your account is awaiting approval" holding page — no access to
   subject pages.
3. Admin (you) receives an email notification (SMTP or SendGrid) with an
   approve/reject link or dashboard entry.
4. On approval, `status = 'approved'` → user can log in and see all five subjects.
5. Every subject/diet/question route checks `status == 'approved'` server-side
   before rendering; anything else redirects to login/pending page.

### 4.2 Suggest Improvement
1. "Suggest Improvement" button on every answer page opens a modal: text box
   (type or paste) + sketch upload.
2. Submit → writes a `pending` row in `suggested_edits` (+ `suggested_edit_sketches`
   if images attached). The live answer is untouched.
3. Admin-only moderation page lists pending suggestions next to the current live
   answer for comparison.
4. On approval, admin may edit the suggested text before publishing. Approving:
   - writes the (possibly amended) text into `canonical_answers.answer_text`
   - logs the prior version into `answer_history`
   - marks the `suggested_edits` row `approved`
5. Rejected suggestions stay in the table (audit trail) but never touch the live
   answer.

---

## 5. Suggested Tech Stack

- **Backend:** Flask or FastAPI + Postgres
- **Frontend:** React, carrying over the navy/amber flashcard aesthetic already
  established (frequency gauges, topic chips, keyboard nav, sketch zoom)
- **Object storage:** DigitalOcean Spaces for sketches/uploaded images (not DB blobs)
- **Email:** SMTP or SendGrid for approval notifications
- **Hosting:** existing DigitalOcean Bangalore droplet, as a second app alongside
  the trading VPS

---

## 6. Suggested Build Order

1. Postgres migrations for all eight tables
2. Auth: signup, login, pending/approved gate, admin flag
3. Read-only content routes: subject → diet → question (written subjects),
   subject → flat list (Oral), using seed/dummy data
4. Data migration script: parse existing flashcard JSON/Python files + UMTC
   content into the new schema — **contingent on resolving the content-sourcing
   question (license UMTC / source raw MCA-SQA papers / re-author answers)**
5. Admin approval queue (member signups)
6. Suggest-improvement modal + submission flow
7. Admin moderation queue (suggested edits) + answer_history versioning
8. Cross-diet "also asked in" feature, sketch upload/display, search + topic chips

---

## 7. Open Item (Unresolved)

Content sourcing for `canonical_answers`. Options discussed:
- License/partner with UMTC for their compiled Q&A content
- Source directly from publicly released MCA/SQA past papers
- Re-author answers independently, citing questions but not reproducing anyone's
  solution text

This should be settled before step 4 (data migration) runs for real, since it
determines what actually populates the answer content at scale.
