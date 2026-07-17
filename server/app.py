from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Any, Optional
from datetime import datetime, timedelta
import random
import os
import logging
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
from pymongo import MongoClient  # type: ignore
from pymongo.errors import PyMongoError  # type: ignore

# ============================================================
# ENV LOADING
# NOTE: this file used to also *create* a placeholder .env if one
# didn't exist. That write (`open(env_path, "w")`) crashed every
# single request on Vercel, because serverless functions run on a
# READ-ONLY filesystem (except /tmp) -- there is no way to write a
# file next to app.py in production, and the previous version tried
# to do exactly that at import time, before any route even ran.
#
# Locally, a missing .env is not a crash -- it's just "no DB
# configured yet" -- so we only ever READ here, never write. If you
# want the create-a-placeholder convenience for local dev, run it as
# a separate one-off script, not inside the app Vercel imports.
# ============================================================
BASE_DIR = Path(__file__).parent.absolute()

env_loaded = False
for env_path in (BASE_DIR / ".env", Path.cwd() / ".env"):
    try:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded .env from: {env_path}")
            env_loaded = True
            break
    except OSError:
        # Read-only or inaccessible filesystem (e.g. some serverless
        # environments) -- just move on, this is not fatal.
        pass

if not env_loaded:
    # Falls back to whatever's already in the process environment --
    # this is exactly how Vercel's dashboard-configured env vars reach
    # the app, since there's no .env file in production at all.
    load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "ATS-Resume")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "resumes")
PORT = int(os.getenv("PORT", 8000))

IS_PLACEHOLDER_URI = "<username>" in MONGODB_URI or "<password>" in MONGODB_URI or "<cluster-host>" in MONGODB_URI

print("\n" + "=" * 70)
print("ENVIRONMENT CONFIGURATION")
print("=" * 70)
if not MONGODB_URI:
    print("MONGODB_URI: NOT SET")
elif IS_PLACEHOLDER_URI:
    print("MONGODB_URI: STILL A PLACEHOLDER -- edit your .env file / Vercel env vars")
else:
    # Never print the password portion of the URI
    safe_uri = MONGODB_URI.split("@")[-1] if "@" in MONGODB_URI else MONGODB_URI[:20]
    print(f"MONGODB_URI: ...@{safe_uri}")
print(f"Database: {MONGODB_DB_NAME}")
print(f"Collection: {MONGODB_COLLECTION}")
print("=" * 70)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
log = logging.getLogger("ATS-Resume")


mongo_client = None
mongo_db = None
mongo_collection = None
mongo_error = None


def init_mongo():
    global mongo_client, mongo_db, mongo_collection, mongo_error

    if not MONGODB_URI or IS_PLACEHOLDER_URI:
        mongo_error = "MONGODB_URI not configured (missing or still a placeholder)"
        log.error(mongo_error)
        return None

    try:
        log.info("Connecting to MongoDB Atlas...")

        parsed = urlparse(MONGODB_URI)
        if parsed.scheme not in {"mongodb", "mongodb+srv"}:
            raise ValueError(f"Unsupported MongoDB URL scheme: {parsed.scheme}")

        # Timeouts kept well under Vercel's Hobby-plan 10s function
        # limit -- the previous 15000ms value could let a slow/blocked
        # connection eat the entire function timeout by itself before
        # Mongo even had a chance to respond.
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
            retryWrites=True,
            w="majority",
        )

        client.admin.command("ping")

        mongo_client = client
        mongo_db = client[MONGODB_DB_NAME]
        mongo_collection = mongo_db[MONGODB_COLLECTION]
        mongo_error = None

        log.info("MongoDB connected successfully!")
        log.info(f"   Database: {MONGODB_DB_NAME}")
        log.info(f"   Collection: {MONGODB_COLLECTION}")

        try:
            mongo_collection.create_index("email")
            mongo_collection.create_index("createdAt")
            mongo_collection.create_index("fullName")
            log.info("Indexes created")
        except PyMongoError as idx_exc:
            log.warning(f"Index creation warning: {idx_exc}")

        return mongo_collection

    except Exception as exc:
        mongo_error = str(exc)
        log.error(f"MongoDB connection failed: {exc}")
        log.info("Troubleshooting tips:")
        log.info("   1. Confirm MONGODB_URI has the correct username/password (no <> placeholders)")
        log.info("   2. In Atlas -> Network Access, confirm 0.0.0.0/0 is ACTIVE, not pending")
        log.info("   3. In Atlas -> Database Deployments, confirm the cluster is not PAUSED")
        log.info("   4. On Vercel, confirm MONGODB_URI is set under Project -> Settings -> Environment Variables")
        mongo_client = None
        mongo_db = None
        mongo_collection = None
        return None


app = FastAPI(
    title="ATS Resume Generator",
    description="AI-powered resume generator with MongoDB storage",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    init_mongo()


class QuickInfo(BaseModel):
    fullName: str
    email: str
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    currentTitle: str = ""
    currentCompany: str = ""
    industry: str = ""
    employmentType: str = "Full-time"
    workMode: str = "Onsite"
    jobLocation: str = ""
    yearsOfExperience: int = 3
    isCurrentlyWorking: bool = False
    degree: str = ""
    fieldOfStudy: str = ""
    university: str = ""
    universityLocation: str = ""
    gpa: str = ""
    startYear: str = ""
    gradYear: str = ""
    enrollmentStatus: str = "Currently Enrolled"
    softSkills: str = ""
    background: str = ""


class GenerateRequest(BaseModel):
    fieldLabel: str
    fieldKey: str
    skillCats: List[str] = []
    keywords: List[str] = []
    entryTypes: List[str] = []
    quickInfo: QuickInfo


class RewriteRequest(BaseModel):
    fieldLabel: str
    sectionType: str
    sectionData: Any
    currentContent: str


class ResumeGenerator:
    def __init__(self):
        self.r = random.Random()

        self.companies = [
            "Stripe", "Shopify", "Atlassian", "HubSpot", "Twilio",
            "Snowflake", "Datadog", "MongoDB", "Microsoft", "Google",
            "Amazon", "Meta", "Apple", "Netflix", "Spotify", "Adobe",
            "Systems Limited", "Netsol", "Arbisoft", "Careem",
            "Daraz", "Finja", "Techlogix", "IBM", "Oracle", "Salesforce",
        ]

        self.verbs = [
            "Developed", "Engineered", "Architected", "Built", "Implemented",
            "Designed", "Created", "Optimized", "Enhanced", "Improved",
            "Streamlined", "Reduced", "Automated", "Led", "Managed",
            "Directed", "Deployed", "Launched", "Migrated", "Integrated",
        ]

        self.metrics = [15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80]
        self.numbers = ["50K", "100K", "250K", "500K", "1M", "2M", "5M"]

        self.templates = {
            "data-scientist": {
                "title": "Senior Data Scientist",
                "summary": "{y}+ years in data science & ML. Built production systems processing millions of data points.",
                "bullets": [
                    "Built ML models achieving {m}% accuracy on {n} daily predictions",
                    "Developed data pipelines processing {n} records",
                    "Led {t} data scientists delivering ML solutions",
                    "Reduced model inference time by {m}%",
                    "Created dashboards serving {n} users",
                ],
            },
            "full-stack-developer": {
                "title": "Senior Full Stack Developer",
                "summary": "{y}+ years building scalable web apps. Proficient in React, Node.js, and cloud.",
                "bullets": [
                    "Architected platform handling {n} requests/sec",
                    "Built React dashboard for {n} users",
                    "Reduced deployment time by {m}%",
                    "Optimized queries improving speed by {m}%",
                    "Led migration to microservices",
                ],
            },
            "software-engineer": {
                "title": "Senior Software Engineer",
                "summary": "{y}+ years building complex systems. Strong CS fundamentals.",
                "bullets": [
                    "Designed system supporting {n} users",
                    "Led development, reducing issues by {m}%",
                    "Built testing framework with {m}% coverage",
                    "Optimized algorithms significantly",
                    "Created microservices handling {n} transactions",
                ],
            },
        }

        self.templates["default"] = self.templates["software-engineer"]

    def b(self, text):
        return (
            text.replace("{m}", str(self.r.choice(self.metrics)))
            .replace("{n}", self.r.choice(self.numbers))
            .replace("{t}", str(self.r.randint(3, 12)))
            .replace("{y}", str(self.r.randint(3, 8)))
        )

    def generate(self, req: GenerateRequest):
        template = self.templates.get(req.fieldKey, self.templates["default"])
        q = req.quickInfo
        y = q.yearsOfExperience or 3
        now = datetime.now()

        if q.background and len(q.background.strip()) >= 10:
            summary = q.background.strip()
        else:
            summary = template["summary"].replace("{y}", str(y))
            if q.industry:
                summary += f" Experienced in the {q.industry} industry."

        experience = []
        if "company" in req.entryTypes or not req.entryTypes:
            exp = {
                "title": q.currentTitle or template["title"],
                "company": q.currentCompany or self.r.choice(self.companies),
                "location": q.location or "Remote",
                "startDate": (now - timedelta(days=y * 365)).strftime("%b %Y"),
                "endDate": "Present" if q.isCurrentlyWorking else (now - timedelta(days=90)).strftime("%b %Y"),
                "current": q.isCurrentlyWorking,
                "bullets": [self.b(self.r.choice(template["bullets"])) for _ in range(3)],
            }
            experience.append(exp)

            if y >= 3:
                prev_end = now - timedelta(days=y * 365)
                prev_start = prev_end - timedelta(days=730)
                other_companies = [c for c in self.companies if c != q.currentCompany] or self.companies
                exp2 = {
                    "title": "Software Engineer",
                    "company": self.r.choice(other_companies),
                    "location": "Remote",
                    "startDate": prev_start.strftime("%b %Y"),
                    "endDate": prev_end.strftime("%b %Y"),
                    "current": False,
                    "bullets": [self.b(self.r.choice(template["bullets"])) for _ in range(2)],
                }
                experience.append(exp2)

        skills = {}
        if req.skillCats and req.keywords:
            spc = max(1, len(req.keywords) // max(1, len(req.skillCats)))
            for i, cat in enumerate(req.skillCats):
                start_idx = i * spc
                end_idx = start_idx + spc
                skills[cat] = ", ".join(req.keywords[start_idx:end_idx][:5])
        else:
            skills = {
                "Technical": "Python, JavaScript, React, Node.js, SQL",
                "Tools": "Git, Docker, AWS, Jenkins",
                "Soft": "Leadership, Communication, Problem Solving",
            }

        projects = []
        if "company" in req.entryTypes or not req.entryTypes:
            projects = [
                {
                    "name": "Analytics Platform",
                    "tech": ", ".join(req.keywords[:3]) if req.keywords else "Python, React",
                    "bullets": [
                        f"Achieved {self.r.choice(self.metrics)}% performance improvement",
                        f"Reduced processing time by {self.r.choice(self.metrics)}%",
                    ],
                },
                {
                    "name": "Customer Dashboard",
                    "tech": ", ".join(req.keywords[2:5]) if len(req.keywords) > 2 else "JavaScript, Node.js",
                    "bullets": [
                        f"Increased user engagement by {self.r.choice(self.metrics)}%",
                        f"Deployed to {self.r.choice(self.numbers)} users",
                    ],
                },
            ]

        education = []
        if "university" in req.entryTypes or not req.entryTypes:
            degree = q.degree or "Bachelor of Science"
            if q.fieldOfStudy:
                degree = f"{degree} in {q.fieldOfStudy}"

            education.append(
                {
                    "degree": degree,
                    "institution": q.university or "National University",
                    "location": q.universityLocation or q.location or "",
                    "startDate": q.startYear or f"{now.year - y - 4}",
                    "endDate": q.gradYear or f"{now.year - y}",
                    "gpa": q.gpa or f"{self.r.uniform(3.0, 4.0):.2f}",
                    "achievements": "Dean's List, Merit Scholarship",
                }
            )

        certifications = [
            {"name": "AWS Certified Solutions Architect", "issuer": "Amazon", "date": str(now.year - 1)},
            {"name": "Professional Certificate", "issuer": "Google", "date": str(now.year)},
        ]

        return {
            "summary": summary,
            "title": q.currentTitle or template["title"],
            "experience": experience,
            "skills": skills,
            "projects": projects,
            "education": education,
            "certifications": certifications,
            "publications": [],
        }


generator = ResumeGenerator()


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "ATS Resume Generator API",
        "version": "1.0.0",
        "mongodb": "connected" if mongo_collection is not None else "disconnected",
        "mongodb_error": mongo_error,
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "mongodb": "connected" if mongo_collection is not None else "disconnected",
        "mongodb_error": mongo_error,
        "database": MONGODB_DB_NAME,
        "collection": MONGODB_COLLECTION,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/test")
async def test_connection():
    return {
        "mongodb_connected": mongo_collection is not None,
        "mongodb_error": mongo_error,
        "database": MONGODB_DB_NAME,
        "collection": MONGODB_COLLECTION,
        "uri_is_placeholder": IS_PLACEHOLDER_URI,
    }


@app.post("/api/generate-resume")
async def generate_resume(request: GenerateRequest):
    try:
        log.info(f"Generating resume for: {request.quickInfo.fullName}")

        data = generator.generate(request)
        q = request.quickInfo

        data["personal"] = {
            "fullName": q.fullName,
            "email": q.email,
            "phone": q.phone,
            "location": q.location,
            "linkedin": q.linkedin,
            "github": q.github,
            "summary": data["summary"],
            "title": data["title"],
        }

        saved_to_db = False
        if mongo_collection is not None:
            try:
                payload = {
                    "fullName": q.fullName.strip(),
                    "email": q.email.strip().lower(),
                    "phone": q.phone.strip(),
                    "location": q.location.strip(),
                    "linkedin": q.linkedin.strip(),
                    "github": q.github.strip(),
                    "currentTitle": q.currentTitle.strip(),
                    "currentCompany": q.currentCompany.strip(),
                    "industry": q.industry.strip(),
                    "fieldKey": request.fieldKey,
                    "fieldLabel": request.fieldLabel,
                    "yearsOfExperience": q.yearsOfExperience,
                    "createdAt": datetime.utcnow(),
                    "resume": data,
                }

                result = mongo_collection.insert_one(payload)
                data["_id"] = str(result.inserted_id)
                saved_to_db = True
                log.info(f"Resume saved to MongoDB with ID: {result.inserted_id}")
            except Exception as db_exc:
                log.warning(f"MongoDB insert failed: {db_exc}")
                data["_id"] = None
        else:
            log.warning("MongoDB not connected - resume not saved")
            data["_id"] = None

        return {
            "success": True,
            "data": data,
            "saved_to_db": saved_to_db,
            "mongodb_connected": mongo_collection is not None,
        }

    except Exception as e:
        log.error(f"Error generating resume: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/rewrite-section")
async def rewrite_section(request: RewriteRequest):
    try:
        data = request.sectionData

        if isinstance(data, dict) and "bullets" in data:
            verbs = [
                "Optimized", "Enhanced", "Streamlined", "Accelerated", "Improved",
                "Transformed", "Revolutionized", "Modernized",
            ]

            data["bullets"] = [
                " ".join(
                    [random.choice(verbs) if i == 0 and len(w) > 3 else w for i, w in enumerate(b.split())]
                )
                for b in data["bullets"]
            ]

        return {"success": True, "data": data, "source": "rewritten"}

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.get("/api/submissions")
async def list_submissions(email: Optional[str] = None, limit: int = 50):
    if mongo_collection is None:
        return JSONResponse(status_code=503, content={"success": False, "error": "MongoDB is not connected"})

    try:
        query = {"email": email.strip().lower()} if email else {}
        docs = list(mongo_collection.find(query).sort("createdAt", -1).limit(min(limit, 200)))

        for d in docs:
            d["_id"] = str(d["_id"])

        return {"success": True, "count": len(docs), "data": docs}

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


if __name__ == "__main__":
    import socket
    import uvicorn  # type: ignore

    # Check the port isn't already bound before uvicorn tries (clearer error message)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", PORT))
        except OSError:
            print(f"\nPort {PORT} is already in use by another process.")
            print("   Windows: run `netstat -ano | findstr :{}` to find the PID,".format(PORT))
            print("   then `taskkill /PID <pid> /F` to stop it, and rerun this script.\n")
            raise SystemExit(1)

    print(f"Server running on: http://0.0.0.0:{PORT}")

    uvicorn.run(app, host="0.0.0.0", port=PORT)