# AI Tools Disclosure

## Tools used

I used two AI tools. The first is Claude, from Anthropic, in a chat interface. The second is an AI coding agent in my code editor, running the Nemotron 3 Ultra Free model.

## What the tools did

Claude helped me understand the assessment brief, plan the order of work, and design and review the knowledge base retrieval and grounding approach, including the checks that stop unsupported answers. The coding agent generated much of the implementation, the automated tests, the evaluation script and the written deliverables in this submission, in response to my instructions. Because much of the code and text was generated, I do not claim to have written every line myself.

## What I did

I prepared the content of the knowledge base documents and decided to leave parking and address out of them on purpose, so that unsupported questions are escalated. I ran the test suite and the evaluation script on my own machine. I built the Docker image, ran the container and checked the health endpoint myself. I reviewed the results and corrected statements in the written deliverables that did not match what I had verified.

## Decisions

The architecture, a controlled workflow in which state changing actions run through validated tools and need patient confirmation, was recommended by the AI tools. I reviewed it and accepted it for this submission.

## Review preparation

During the live review I will walk through the request flow, the tool layer, the workflow and the retrieval, and I will say so plainly when I do not know something.

## Confidentiality

All data in the project is synthetic and I shared no confidential data with the tools. To the best of my knowledge the submission contains no fabricated sources, metrics or claims.