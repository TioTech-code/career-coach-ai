# AI Career Coach

#### Video Demo:https://youtu.be/FBm5_-Rc628

## Description

AI Career Coach is a web application built using Python, Flask, HTML, CSS and the Groq API. The purpose of the application is to help students improve their CVs and prepare for software engineering degree apprenticeship applications using artificial intelligence.

When a user opens the application, they are presented with a homepage where they can begin using the system. They can then navigate to the dashboard, which provides access to the CV Review feature.

The main feature of the application is the AI-powered CV review. Users can either paste the text of their CV into a text box or upload a CV as a PDF document. The application extracts the text from the PDF if one is uploaded. The CV text is then sent to the Groq API, which analyses it and returns personalised feedback.

The feedback includes strengths, suggested improvements, additional skills that could be added, interview questions, and general advice. This allows users to understand how they can improve their CV before applying for jobs, apprenticeships, or university courses.

I chose to build this project because I am interested in software engineering and artificial intelligence. I wanted to create something practical that solves a real problem for students who are preparing their first professional CV.

## Design Choices

I chose Flask because it is lightweight, easy to understand, and well suited for web applications. Flask also separates the backend Python code from the frontend HTML templates, making the application easier to organise.

I decided to use HTML templates instead of creating the entire interface inside Python because templates are easier to maintain and allow the website to have multiple pages.

The Groq API was selected because it provides fast AI responses and offers a free tier suitable for educational projects. Environment variables stored in a `.env` file are used to keep the API key secure instead of placing it directly inside the source code.

The application uses CSS to provide a clean and modern appearance while remaining simple to navigate.

## Project Structure

### app.py

This file contains the Flask application, routes, form processing, PDF handling, and communication with the Groq API.

### templates/

This folder contains all HTML pages used by the application.

- index.html – Homepage
- dashboard.html – Dashboard page
- cv_review.html – Form for uploading or pasting a CV
- results.html – Displays the AI-generated feedback

### static/

This folder contains the CSS styling and any JavaScript used by the application.

### uploads/

This folder temporarily stores uploaded PDF files before they are processed.

### requirements.txt

Lists the Python packages required to run the project.

### README.md

Contains documentation explaining how the project works and how to run it.

## Technologies Used

- Python
- Flask
- HTML
- CSS
- Groq API
- python-dotenv
- PyPDF

## How to Run

1. Clone or download the project.

2. Install the required packages.

```
pip install -r requirements.txt
```

3. Create a `.env` file containing:

```
GROQ_API_KEY=your_api_key_here
```

4. Run the application.

```
python app.py
```

5. Open:

```
http://127.0.0.1:5000
```

## Challenges

The biggest challenge during development was integrating an AI API into the Flask application while keeping the API key secure. Another challenge was adding PDF support so users could upload CVs instead of only pasting text. Learning how to extract text from PDF files and send it to the AI model required careful testing.

## Future Improvements

If I continue developing this project, I would like to add:

- User accounts
- Saved CV history
- CV scoring
- Tailored feedback for specific job descriptions
- Mock interview mode
- Improved dashboard
- Dark mode
- Online deployment

Overall, this project helped me gain experience with Flask, web development, AI integration, APIs, file uploads, and secure handling of environment variables.