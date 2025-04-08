# Yorkshire Crypto Exchange 🚀

Yorkshire Crypto Exchange is a microservices-based cryptocurrency exchange platform designed for secure and efficient fiat-to-crypto transactions, wallet management, and trade execution. Built using Flask, Next.js, Node.js, Typescript, PostgreSQL, RabbitMQ, and Docker, it follows REST API best practices and utilizes message queues for asynchronous processing. This project is part of the Enterprise Solution Design (ESD) course, demonstrating scalability, modularity, and real-world financial transaction handling in a containerized environment.

## 🛠 Tech Stack

- **Database:** PostgreSQL
- **Website:** Next.js, Typescript (Vercel V0)
- **API:** Flask + Pika (RabbitMQ) + Kong API gateway
- **ORM:** Flask-Migrate + SQLAlchemy
- **CI/CD:** GitHub Actions
- **Python Formatting:** Black (PEP8 style guide)
- **Auto-generate Changelog:** Release Changelog Builder
- **Authentication** JSON Web Tokens (JWT)
- **API Documentation:** Flask-RESTx
- **Coding Standards:** Pylint
- **Containerization:** Docker-Compose (Database, APIs, Website, RabbitMQ)

## 📜 Documentation

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development setup and coding standards
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines, branching strategy, and PR guide
- **[CHANGELOG.md](CHANGELOG.md)** - Automatically generated changelog

## 📥 Installation & Setup

### Set up docker containers
1. Install Python dependencies:
   ```sh
   pip install -r requirements.txt
   ```

2. Get bash command from @tanzhongyan to get .env files required to run the project.

3. Start the services using Docker Compose:
   ```sh
   docker-compose up -d --build
   ```

### Access API documentation:
**Consolidated API documentation**
Go to [link](http://localhost:3001/swagger-ui) after `docker-compose up -d --build`.

**Independent API documentation**
   - **Atomic microservices**
      - **Fiat Service:** `http://localhost:5001/api/v1/fiat`
      - **Crypto Service:** `http://localhost:5002/api/v1/crypto`
      - **User Service:** `http://localhost:5003/api/v1/user`
      - **transaction Service:** `http://localhost:5005/api/v1/transaction`
   - **Composite microservices**
      - **identity** `http://localhost:5004/api/v1`
      - **deposit** `http://localhost:5006/api/v1`
      - **ramp** `http://localhost:5007/api/v1`
      - **market** `http://localhost:5008/api/v1`
      - **initiate** `http://localhost:5009/api/v1/`
      - **complete** `http://localhost:5010/api/v1/`

### Set up front end website
1. Install Dependencies

Before running the website, navigate to the project directory and install the necessary dependencies:

```sh
cd website/yorkshire-crypto-exchange
npm install
```

Alternatively, if using Yarn:

```sh
cd website/yorkshire-crypto-exchange
yarn install
```

2. Run the Development Server

To start the Next.js development server, run:

```sh
npm run dev
```

Or, if using Yarn:

```sh
yarn dev
```

Once the server starts, the website will be available at:

```
http://localhost:3000
```

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
