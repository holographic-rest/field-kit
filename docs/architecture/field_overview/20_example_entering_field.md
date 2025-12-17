PAGE 20 – Example Flow: Entering the Field

Title: EXAMPLE – Entering the Field (Layers 3 ↔ 4)

8.2 Entering the Field (Layers 3 ↔ 4)

Client → Reverse proxy → Load balancer → API Gateway

Gateway:

Validates JWT (Auth).

Checks rate limits (Redis).

Logs a Q-event to QDPI Log via gRPC → Kafka.

User = Student X; role = Student.

Page = 247; question text.

HPU = (Student, Queue, public/private).

Gateway forwards the request to AI Orchestrator / Field Engine, with:

User, role, page, question.

QDPI metadata + trace ID.