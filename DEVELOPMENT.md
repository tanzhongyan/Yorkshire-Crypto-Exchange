# Deployment Guide

This guide provides step-by-step instructions on setting up and deploying this project.

## Setting Up Your Local Environment

Before running the project, ensure you have Python installed and install dependencies:

1. **Verify Python Installation**

   ```sh
   python --version
   ```

   Ensure Python version **3.9 or earlier** is installed.

   Do this inside VSCode terminal. If the output is an error, check the following:
   - In search bar, search "add or remove programs". Search "python" within "add or remove programs". It should show the version of python you have installed.
   - If there's nothing there, install it at [python.org](https://www.python.org/downloads/). The latest stable version is version 3.13.
   - After installing it, in VSCode, press `ctrl` + `shift` + `p` and search "python: create environment". Click on "Venv". Click on the latest version of python you have. Tick "requirements.txt" checkbox and press "OK". Your repository should now have a ".venv" file.

2. **Install Required Dependencies**
   Navigate to the project's root directory and install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

## Running Docker Compose

To initialise and start the database and microservices, run:

```sh
docker-compose up -d --build
```

- `-d` runs the services in the background.
- `--build` rebuilds images before starting containers.

### How It Works

1. **Docker Compose builds the database container first**:
   - Traditionally, `depends_on` runs services immediately after the container is up.
   - A **healthcheck** is added to ensure the database is fully set up before other services start.

If you face issues when deploying the postgres container like "user_db" not found, it is likely caused by an incompatibility issue between windows and linux line endings.

- Run:

   ```sh
   docker-compose down -v
   ```

- In your VSCode local terminal, run:

   ```sh
   wsl dos2unix ./database/create-multiple-postgresql-databases.sh
   ```

- Run:

   ```sh
   docker-compose up -d --build
   ```

2. **Microservices start after the database is ready**:
   - Navigate into the respective microservice directory before running migrations:

     ```sh
     cd ./api/atomic/user  # or ./api/atomic/fiat, ./api/atomic/crypto
     ```

   - The migration file is executed to initialise database tables.
   - `app.py` starts after migrations complete.

3. **Seeding Data (First-Time Setup)**:
   - If this is the first time running, `app.py` will populate the database using `seeddata.json`.

## Flask Migrate

[Flask-Migrate](https://flask-migrate.readthedocs.io/) is used as an ORM for database management.

### Benefits

- Reduces the need for raw SQL queries.
- Simplifies schema management for future cloud deployment.

### First-Time Database Migration

Navigate to the microservice folder first:

```sh
cd ./api/atomic/user  # or ./api/atomic/fiat, ./api/atomic/crypto
```

Run the following commands to create the migration files and apply them:

```sh
flask db init
flask db migrate -m "Initial migration."
flask db upgrade
```

Migration files should appear inside the `migrations/` folder.

### Example Table Definition

```python
class UserAccount(db.Model):
    __tablename__ = 'user_account'
    user_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(50), unique=True, nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)

    # Relationships
    authentication = db.relationship('UserAuthenticate', back_populates='user', uselist=False, cascade='all, delete-orphan')
    addresses = db.relationship('UserAddress', back_populates='user', cascade='all, delete-orphan')
```

## Flask-RESTx

[Flask-RESTx](https://flask-restx.readthedocs.io/) is used to automatically generate API documentation.

### Example of Flask-RESTx Model Setup

```python
user_model = api.model('UserAccount', {
    'user_id': fields.String(readOnly=True, description='The unique identifier of a user'),
    'username': fields.String(required=True, description='The username'),
    'fullname': fields.String(required=True, description='The full name'),
    'phone': fields.String(required=True, description='The phone number'),
    'email': fields.String(required=True, description='The email address')
})
```

### CRUD Example

```python
@api.route(f'{API_ROOT}/user/account')
class UserAccountListResource(Resource):
    @api.marshal_list_with(user_model)
    def get(self):
        """Fetch all user accounts"""
        return UserAccount.query.all()

    @api.expect(user_model)
    @api.marshal_with(user_model, code=201)
    def post(self):
        """Create a new user account"""
        data = request.json
        new_user = UserAccount(
            username=data.get('username'),
            fullname=data.get('fullname'),
            phone=data.get('phone'),
            email=data.get('email')
        )
        db.session.add(new_user)
        db.session.commit()
        return new_user, 201
```

### Accessing API Documentation

Each microservice hosts its documentation at:

- **Fiat Service:** `http://localhost:5001/docs`
- **Crypto Service:** `http://localhost:5002/docs`
- **User Service:** `http://localhost:5003/docs`

## Accessing Database Data (Visualisation)

You can visualise database data using **DBeaver**:

1. **Download and install [DBeaver](https://dbeaver.io/)**.
2. **Create a PostgreSQL connection** with the following credentials:
   - **Host:** `localhost`
   - **Port:** `5433`
   - **Username:** `user`
   - **Password:** `password`
3. Click **OK**, then connect. You can now browse and query your database.

This guide ensures a smooth setup and deployment process. Happy coding!
