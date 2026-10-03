# Assumptions

## Clinic operations

The clinic is open Sunday to Thursday and closed on Friday and Saturday. Appointments are offered at 09:00, 10:00, 11:00, 14:00 and 15:00, and these times are fixed. Each of the three specialties, cardiology, dermatology and general practice, has one doctor, so only one appointment can exist for a given specialty, date and time. Appointments can be booked from tomorrow up to 14 days ahead. Patient identifiers are the letter P followed by four digits. Appointment identifiers use the prefix APT, a hyphen and four digits.

## Data and privacy

All data is synthetic and no real patient information is used. In production the patient identifier would come from an authenticated session. In this submission it is accepted in the request body, and the service reads it from the message text only when the body does not supply it. Logs record the request identifier, intent and status, and never the message text. Escalation tickets store a reason code and not the patient's message.

## Knowledge base

The knowledge base is the only source for answers about preparation, insurance, hours and cancellation. Preparation instructions are general, and instructions from the patient's own doctor are not modelled. The assistant never confirms that a specific insurer is accepted. Parking and address are deliberately absent so that such questions are escalated and not guessed. Each document carries a document identifier, title, owner, review date and a flag that controls whether it is searchable.

## Technical

The service runs as a single process with an in memory store. The date comes from the server clock, and a production deployment would use the Asia/Riyadh time zone. Intent detection is rule based and retrieval is lexical, which I consider sufficient for seven intents and four short documents. Grounding means that every answer cites retrieved text and the citation check rejects any other source. No model based judge is used. The test suite was run locally on Python 3.14, and the Docker image uses Python 3.11.

## Evaluation

The fifteen evaluation cases represent the critical paths and are not exhaustive. A tool timeout is simulated by making the store call fail inside the test, because real network timeouts need infrastructure. Prompt injection is tested with one adversarial message and is not a full red team exercise.

## Out of scope

Regulatory compliance, real insurance eligibility checks, multi clinic scheduling, patient applications, messaging or voice channels, the Hijri calendar and prayer times, Arabic dialects, backup and disaster recovery are outside the scope of this submission and would need validation before use.