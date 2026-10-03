# What Works, What Does Not, What I Would Build Next

## What Works

The service exposes POST /assistant/message, validated with Pydantic, and supports seven intents: booking, rescheduling, cancellation, availability, preparation instructions, insurance and general information, and escalation to a human. Intent detection is rule based, which keeps behaviour deterministic and testable without an API key. It sits behind two functions, classify and extract_entities, so a language model classifier can replace it without changing the rest of the service.

Answers to clinic questions come from a knowledge base of four markdown documents, each with a document identifier, owner and review date. Retrieval requires a minimum share of the meaningful words in the question to match, and the answer is copied from the retrieved text together with its source. A question the knowledge base cannot support, such as one about parking, is escalated to staff and is never guessed. A grounding check rejects any answer that cites a source that was not retrieved.

Actions run through six validated tools. A wrapper converts any exception, including a timeout, into a failed result, so the assistant reports success only after the scheduling system confirms the change. The reschedule flow is exercised over two messages through the API: it asks for missing details, verifies that the appointment belongs to the patient, checks the new slot, asks the patient to confirm, and only then executes. Emergency wording ends the flow and escalates immediately. A guardrails module screens each message before any action for attempts to override instructions, requests about another patient and requests for medical advice, and eight tests cover it. A patient cannot read or change another patient's appointment, and logs and escalation tickets hold no message text.

The repository contains 46 automated tests and 15 evaluation cases with expected behaviour and pass criteria. All of them pass. The evaluation cases cover booking, double booking, a closed day, missing details, ownership, the confirmation step, a tool timeout, a knowledge base answer, an unsupported question, an adversarial instruction, a request for medical advice, an emergency, an invalid identifier and an ambiguous request. A shared test fixture clears workflow state between tests. I built the Docker image, ran the container and confirmed that the health endpoint and the message endpoint respond.

## What Does Not Work

The scheduling store and the workflow state are held in memory. Data and in progress reschedule flows are lost on restart, nothing expires, and the service works only as a single process.

Intent detection and retrieval are lexical. They miss paraphrases, typing mistakes and Arabic wording, and the service handles English only. Patients who phrase a question differently will be escalated more often than necessary. This is a safe failure, but it adds work for staff.

The service has no authentication. The patient identifier is accepted in the request body, and a production deployment would take it from an authenticated session. There is also no rate limiting, structured monitoring or deployment pipeline.

The guardrails recognise known phrasing and are not a complete defence against prompt injection. Free text is not passed to a language model today, which limits exposure, but adding a model would require stronger controls and new tests.

The project declares a minimum Python version of 3.11 and the Docker image uses Python 3.11, but I ran the test suite locally on Python 3.14. The tests have not been run inside the container.

The knowledge base is sample data written for this assessment and is not a real clinic policy. Medical, insurance and regulatory content would need validation by the clinic before use.

## Highest Risk Behaviour Not Covered by Tests

Concurrent booking. Two simultaneous requests for the same slot can both pass the availability check and both book, because the in memory store has no locking. A database with row level locking, applied inside the booking tool, would remove the risk.

## What I Would Build Next

First, replace the in memory store and workflow state with a database that supports locking and a shared session store, add authentication, and add structured logs, metrics and rate limiting. Second, add embedding based retrieval beside the current lexical retriever, measure recall and grounding precision, and add Arabic support. Third, place a language model behind the existing intent detection seam, controlled by a feature flag and with the rule based classifier as fallback, and compare intent accuracy, entity accuracy and latency. Fourth, confirm local requirements with the clinic, such as the Hijri calendar, prayer times and the applicable Saudi data protection and health sector rules, before adding any related behaviour.