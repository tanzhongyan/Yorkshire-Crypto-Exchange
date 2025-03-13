# Yorkshire Crypto Exchange 🚀

Yorkshire Crypto Exchange is a microservices-based cryptocurrency exchange platform designed for secure and efficient fiat-to-crypto transactions, wallet management, and trade execution. Built using Flask, Next.js, Node.js, Typescript, PostgreSQL, RabbitMQ, and Docker, it follows REST API best practices and utilizes message queues for asynchronous processing. This project is part of the Enterprise Solution Design (ESD) course, demonstrating scalability, modularity, and real-world financial transaction handling in a containerized environment.

## 🛠 Tech Stack

- **Database:** PostgreSQL
- **Website:** Next.js, Node.js, Typescript (Vercel V0)
- **API:** Flask + Pika (RabbitMQ)
- **ORM:** Flask-Migrate + SQLAlchemy
- **CI/CD:** GitHub Actions
- **Python Formatting:** Black (PEP8 style guide)
- **Auto-generate Changelog:** Release Changelog Builder
- **API Documentation:** Flask-RESTx
- **Coding Standards:** Pylint
- **Containerization:** Docker-Compose (Database, APIs, Website, RabbitMQ)

## 📜 Documentation

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development setup and coding standards
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines, branching strategy, and PR guide
- **[CHANGELOG.md](CHANGELOG.md)** - Automatically generated changelog

## 📥 Installation & Setup

1. Install Python dependencies:
   ```sh
   pip install -r requirements.txt
   ```

2. Start the services using Docker Compose:
   ```sh
   docker-compose up -d --build
   ```

3. Access API documentation:
   - **Atomic microservices**
      - **Fiat Service:** `http://localhost:5001/docs`
      - **Crypto Service:** `http://localhost:5002/docs`
      - **User Service:** `http://localhost:5003/docs`
   - **Composite microservices**
      - **identity** `http://localhost:5004/v1/api`

## 📌 Features
- **Secure transactions** between fiat and crypto
- **Microservices architecture** with modular scalability
- **Message queue processing** using RabbitMQ
- **Automated API documentation** with Flask-RESTx
- **Containerized deployment** with Docker

## 🤝 Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting changes, PRs, and reviewing contributions.

## 📝 License
This project is licensed under the [MIT License](LICENSE).