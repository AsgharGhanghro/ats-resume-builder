# 📄 ATS Resume Builder — AI Powered Resume Generator

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)

> **An AI-powered resume builder** that generates ATS-friendly, professional resumes from a short bio. Pick a career field, answer a quick step-by-step form, and get a polished resume with a live ATS score — exportable as **PDF** or **DOCX**. Built with a FastAPI + MongoDB backend and a vanilla JS frontend, deployed on Vercel.

**🌐 Live Demo:** [ats-resumes-builder](https://ats-resume-builder-six-theta.vercel.app/)  
**📁 GitHub Repo:** https://github.com/AsgharGhanghro/ats-resume-builder/

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [How It Works](#-how-it-works)
- [Career Fields & ATS Scoring](#-career-fields--ats-scoring)
- [Deployment](#-deployment)
- [Future Improvements](#-future-improvements)
- [Contributing](#-contributing)
- [License](#-license)
- [Creators](#-creators)

---

## 🌟 Overview

This project combines a **rule-based/AI resume generator** with a **full in-browser editor**. The backend (`app.py`) builds a structured resume from the details you provide, and the frontend (`index.html`) lets you fine-tune every section, watch your ATS score update live, reorder sections, switch templates, and export a recruiter-ready file.

Perfect for tailoring a fresh, ATS-optimized resume for every job application in minutes.

---

## ✨ Features

- 🎯 **20+ Career Fields** — Data Scientist, Full-Stack Dev, DevOps, PM, UX Designer, and more, each with its own tuned keyword set
- 🤖 **AI-Assisted Generation** — turns a short bio into a full, structured resume (summary, experience, skills, projects, education)
- 📊 **Live ATS Score** — real-time keyword coverage + resume health checklist, right in the editor
- 🎨 **4 Templates** — Professional, Classic, Minimal, Modern — switch instantly with no data loss
- 🖊️ **Full Editor** — drag-and-drop section order, show/hide sections, adjustable font sizes, undo/redo
- 💾 **Autosave + Saved Versions** — tailor multiple resumes per job application, all saved on-device
- 📤 **Real Exports** — multi-page **PDF** with clickable links, and an ATS-safe **DOCX** with real headings/bullets
- 🌗 **Light / Dark / System Theme**
- 🗄️ **MongoDB Storage** — submissions are saved securely to support saved-resume features

---

## 📁 Project Structure

```
ATS/
│
├── client/                      # Frontend (web interface)
│   ├── index.html               # Entire app: UI, state, PDF/DOCX export
│   ├── AI_Resume.mp4            # Intro splash video
│   └── vercel.json               # Vercel config (Root Directory: client)
│
├── server/                      # Backend (API + resume generator)
│   ├── app.py                   # FastAPI routes, ResumeGenerator, Mongo layer
│   ├── requirements.txt         # Python dependencies
│   ├── network_diagnosis.py     # Mongo connectivity debug script
│   ├── test_mongo.py            # Mongo connection smoke test
│   ├── .env                     # MONGODB_URI, DB name, collection (local only)
│   └── vercel.json               # Vercel config (Root Directory: server)
│
└── README.md                    # Project documentation
```

> **Note:** `client` and `server` are deployed as **two separate Vercel projects** from this one repo, each with its own Root Directory setting — this keeps the static frontend from ever shadowing the API routes.

---

## 🚀 Getting Started

### Prerequisites

- Python **3.8 or higher**
- pip (Python package manager)
- Git
- A modern web browser
- A MongoDB Atlas cluster (free tier works)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/ATS.git
cd ATS
```

### 2. Backend Setup

```bash
cd server
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create `server/.env`:
```env
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-host>/
MONGODB_DB_NAME=xxxx
MONGODB_COLLECTION=xxxx
```

Start the backend:
```bash
python app.py
```

Server runs at **http://localhost:8000**

### 3. Frontend Setup

```bash
cd ../client
npx serve .
```

Open your browser at the address `serve` gives you (usually **http://localhost:3000**).

If testing locally, point the frontend at your local backend — in `index.html`:
```js
const API = 'http://localhost:8000';
```

---

## 🧠 How It Works

```
Quick-Info Wizard (client/index.html)
      │
      ▼
POST /api/generate-resume (server/app.py)
  - ResumeGenerator picks a field template
  - Fills summary, experience, skills, projects, education
  - Injects field-specific ATS keywords
      │
      ▼
MongoDB Atlas
  - Submission stored securely for saved-resume features
      │
      ▼
Live Editor (client/index.html)
  - User edits every field, reorders sections, switches templates
  - ATS score recalculates in real time
      │
      ▼
Export
  - jsPDF + html2canvas → multi-page PDF with clickable links
  - docx.js → ATS-safe Word document
```

### Resume Generation Pipeline

1. **Field Selection** — user picks a career field (keywords + skill categories are pre-tuned per field)
2. **Quick-Info Wizard** — 6 focused steps: basics, contact, links, background, soft skills, about-you
3. **Generation** — `ResumeGenerator` (in `app.py`) builds experience, projects, skills, and education from the answers
4. **ATS Scoring** — keywords found in bullets/summary count fully, keywords only listed in Skills count half, plus a structural health checklist
5. **Editing** — every field is editable, with undo/redo and autosave
6. **Export** — PDF (image-based, paginated, with real clickable links) or DOCX (built from data, not a snapshot, for cleaner ATS parsing)

---

## 📊 Career Fields & ATS Scoring

Each field in `FIELDS` (client-side) carries its own:

| Property | Description |
|---|---|
| `keywords` | ATS keywords scored against your bullets, summary, and projects |
| `skillCats` | Skill category labels shown in the Technical Skills section |
| `accent` | Theme color used in the field picker card |

The ATS score (visible as a ring in the editor header) combines:
- **Keyword coverage** (up to 55 points) — full credit if a keyword is demonstrated in a bullet/summary/project, half credit if only listed under Skills
- **Structure checklist** (up to 45 points) — email present, phone present, work experience listed, bullets contain metrics, 2+ skill categories filled, summary written, no near-duplicate bullets

---

## 🌐 Deployment

This project is deployed on **Vercel** as **two separate projects** from the same repo.

| Project | Root Directory | Notes |
|---|---|---|
| Frontend | `client` | Framework preset: **Other** |
| Backend | `server` | Add `MONGODB_URI` under Settings → Environment Variables |

### Deploy Your Own Copy

1. Fork this repository
2. Go to [vercel.com](https://vercel.com) → **New Project**
3. Import your forked repo **twice** — once with Root Directory `client`, once with Root Directory `server`
4. Add your MongoDB env vars to the backend project
5. Update `const API = '...'` in `client/index.html` to point at your deployed backend URL
6. Redeploy both — your app is live! 🎉

`server/vercel.json`:
```json
{
  "version": 2,
  "builds": [{ "src": "app.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/(.*)", "dest": "app.py" }]
}
```

---

## 🔮 Future Improvements

- [ ] Real AI model integration for section rewriting (currently rule-based)
- [ ] More resume templates
- [ ] Cover letter generator
- [ ] Public resume-sharing links
- [ ] Team/recruiter view mode
- [ ] Resume comparison against a job description
- [ ] Multi-language resume support
- [ ] Public REST API with API keys

---

## 🤝 Contributing

Contributions are welcome! Here's how:

1. **Fork** the repository
2. Create a feature branch
   ```bash
   git checkout -b feature/YourFeature
   ```
3. Commit your changes
   ```bash
   git commit -m "feat: add YourFeature"
   ```
4. Push to your branch
   ```bash
   git push origin feature/YourFeature
   ```
5. Open a **Pull Request**

---

## 📄 License

MIT License — Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.

---

##  Creator

Ali Asghar 

- 🐙 GitHub: https://github.com/AsgharGhanghro/ats-resume-builder/
- 📧 Email: aliasghargh540@gmail.com
- 🔗 Project: https://ats-resume-builder-six-theta.vercel.app/

---

## 🙏 Acknowledgments

- FastAPI & MongoDB documentation and community
- jsPDF, html2canvas, and docx.js maintainers
- Vercel for free hosting

---

⭐ **If this project helped you land an interview, give it a star!**

---

*Made with Python, FastAPI, and a lot of resume formatting patience 📄*
