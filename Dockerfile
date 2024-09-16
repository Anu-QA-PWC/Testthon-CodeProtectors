# Use a base image with Python installed
FROM python:3.8

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Run the tests using Pytest with Behave
CMD ["python", "invoke.py"]
