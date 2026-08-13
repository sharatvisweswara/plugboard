---
name: simple-english
description: Write in ASD-STE100-derived Simplified Technical English — short sentences, one word per meaning, active voice, no hedging modals, condition before command. Use for docs, READMEs, commit messages, PR descriptions, error messages, runbooks, and general prose.
---

# simple-english

Condensed rules, paraphrased from ASD-STE100 Simplified Technical English
(the aerospace maintenance-manual standard). Full spec:
https://www.asd-ste100.org/. Reference implementation this was adapted
from: https://github.com/AminBlg/SimpleEnglish.

1. **Max ~20 words per sentence.** Split anything longer.
2. **One word, one meaning.** Pick one verb per concept (e.g. always
   "check", never alternate check/verify/confirm/validate) and use it
   consistently for the rest of the document.
3. **Simple tenses only.** "We updated the config" — not "the config has
   been updated" or "the config will have been updated."
4. **No "-ing" clauses tacked onto a sentence.** Split into two sentences
   instead of ", making it easier to..." or ", allowing users to...".
5. **Active voice.** "The deploy script writes the log" — not "the log is
   written by the deploy script."
6. **No hedging modals.** Ban should/would/may/might. Keep can/will/must —
   they state capability, futurity, or requirement, not a hedge.
7. **Condition before command.** "If the flag is set, skip the cache" —
   not "skip the cache if the flag is set." State the condition before
   the instruction, not after.
8. **One instruction per sentence.** Don't chain steps with "and" or
   semicolons.
9. **Keep articles and "that."** This is short, not terse — "the database
   connection failed," not "database connection failed." Dropping
   articles is a different compression style; this one stays
   grammatical.

Applies broadly — chat replies and written deliverables alike, once this
plugin is installed. No on/off toggle; it's ambient once loaded.

Don't cite a rule number. This paraphrase is deliberately unnumbered —
it doesn't match the real ASD-STE100 numbering, and guessing at one
produces exactly the confident-but-wrong output this skill exists to
prevent.
