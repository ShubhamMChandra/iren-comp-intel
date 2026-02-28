"""
Seed the database with initial prospect and competitor companies.

Prospects: AI labs, enterprise AI companies, well-funded AI startups, hyperscalers
           needing overflow — the companies most likely to need HPC/GPU capacity.

Competitors: Neoclouds, hyperscaler internal builds, traditional DC REITs,
             power-first players, and international competitors.
"""

from database.db import get_session, init_db
from database.models import Company

PROSPECTS = [
    # --- AI Labs / Foundation Model Companies ---
    {
        "name": "OpenAI",
        "industry": "AI Research / Foundation Models",
        "website": "https://openai.com",
        "description": "Leading AI lab behind GPT series. Massive and growing compute needs for training and inference.",
        "hq_location": "San Francisco, CA",
        "employee_count": 3000,
        "is_public": False,
        "total_funding": 17_600_000_000,
    },
    {
        "name": "Anthropic",
        "industry": "AI Research / Foundation Models",
        "website": "https://anthropic.com",
        "description": "AI safety company building Claude models. Rapidly scaling compute for training runs.",
        "hq_location": "San Francisco, CA",
        "employee_count": 1500,
        "is_public": False,
        "total_funding": 15_000_000_000,
    },
    {
        "name": "xAI",
        "industry": "AI Research / Foundation Models",
        "website": "https://x.ai",
        "description": "Elon Musk's AI company building Grok. Operating massive Colossus GPU cluster.",
        "hq_location": "Austin, TX",
        "employee_count": 500,
        "is_public": False,
        "total_funding": 12_000_000_000,
    },
    {
        "name": "Mistral AI",
        "industry": "AI Research / Foundation Models",
        "website": "https://mistral.ai",
        "description": "European AI lab building open-weight models. Growing compute footprint.",
        "hq_location": "Paris, France",
        "employee_count": 700,
        "is_public": False,
        "total_funding": 2_200_000_000,
    },
    {
        "name": "Cohere",
        "industry": "AI Research / Enterprise AI",
        "website": "https://cohere.com",
        "description": "Enterprise-focused AI company building language models for business use cases.",
        "hq_location": "Toronto, Canada",
        "employee_count": 500,
        "is_public": False,
        "total_funding": 970_000_000,
    },
    {
        "name": "AI21 Labs",
        "industry": "AI Research / Enterprise AI",
        "website": "https://ai21.com",
        "description": "Building foundation models for enterprise. Jamba model family.",
        "hq_location": "Tel Aviv, Israel",
        "employee_count": 350,
        "is_public": False,
        "total_funding": 336_000_000,
    },
    {
        "name": "Stability AI",
        "industry": "AI Research / Generative AI",
        "website": "https://stability.ai",
        "description": "Open-source generative AI company (Stable Diffusion). Needs large GPU clusters for training.",
        "hq_location": "London, UK",
        "employee_count": 200,
        "is_public": False,
        "total_funding": 260_000_000,
    },
    {
        "name": "Inflection AI",
        "industry": "AI Research / Foundation Models",
        "website": "https://inflection.ai",
        "description": "AI studio building personal AI assistants. Previously operated large GPU cluster.",
        "hq_location": "Palo Alto, CA",
        "employee_count": 200,
        "is_public": False,
        "total_funding": 1_525_000_000,
    },
    {
        "name": "Character.AI",
        "industry": "AI / Consumer",
        "website": "https://character.ai",
        "description": "Conversational AI platform with massive inference demand. Licensed tech to Google.",
        "hq_location": "Menlo Park, CA",
        "employee_count": 250,
        "is_public": False,
        "total_funding": 350_000_000,
    },
    {
        "name": "Perplexity AI",
        "industry": "AI / Search",
        "website": "https://perplexity.ai",
        "description": "AI-powered search engine. Rapidly scaling inference infrastructure.",
        "hq_location": "San Francisco, CA",
        "employee_count": 300,
        "is_public": False,
        "total_funding": 900_000_000,
    },
    # --- Well-Funded AI Startups Scaling Infrastructure ---
    {
        "name": "Scale AI",
        "industry": "AI / Data Infrastructure",
        "website": "https://scale.com",
        "description": "Data labeling and AI infrastructure for enterprises and government. Large GPU needs for RLHF.",
        "hq_location": "San Francisco, CA",
        "employee_count": 1000,
        "is_public": False,
        "total_funding": 1_600_000_000,
    },
    {
        "name": "Databricks",
        "industry": "Data / AI Platform",
        "website": "https://databricks.com",
        "description": "Unified data and AI platform. Runs massive GPU workloads for customers' model training.",
        "hq_location": "San Francisco, CA",
        "employee_count": 7000,
        "is_public": False,
        "total_funding": 4_200_000_000,
    },
    {
        "name": "Hugging Face",
        "industry": "AI / ML Platform",
        "website": "https://huggingface.co",
        "description": "Open-source AI platform and model hub. Expanding compute for inference endpoints.",
        "hq_location": "New York, NY",
        "employee_count": 400,
        "is_public": False,
        "total_funding": 395_000_000,
    },
    {
        "name": "Weights & Biases",
        "industry": "AI / MLOps",
        "website": "https://wandb.ai",
        "description": "ML experiment tracking and model management platform used by most AI teams.",
        "hq_location": "San Francisco, CA",
        "employee_count": 400,
        "is_public": False,
        "total_funding": 250_000_000,
    },
    {
        "name": "Anyscale",
        "industry": "AI / Distributed Computing",
        "website": "https://anyscale.com",
        "description": "Makers of Ray. Platform for scalable AI compute orchestration.",
        "hq_location": "San Francisco, CA",
        "employee_count": 300,
        "is_public": False,
        "total_funding": 260_000_000,
    },
    {
        "name": "Modal",
        "industry": "AI / Cloud Infrastructure",
        "website": "https://modal.com",
        "description": "Serverless GPU cloud for AI workloads. Growing rapidly as alternative to big cloud.",
        "hq_location": "New York, NY",
        "employee_count": 100,
        "is_public": False,
        "total_funding": 110_000_000,
    },
    {
        "name": "Together AI",
        "industry": "AI / Inference Platform",
        "website": "https://together.ai",
        "description": "Open-source AI inference and training platform. Large GPU fleet for serving models.",
        "hq_location": "San Francisco, CA",
        "employee_count": 200,
        "is_public": False,
        "total_funding": 325_000_000,
    },
    {
        "name": "Runway",
        "industry": "AI / Creative Tools",
        "website": "https://runwayml.com",
        "description": "AI-powered creative tools and video generation. Massive GPU needs for Gen-3 model.",
        "hq_location": "New York, NY",
        "employee_count": 200,
        "is_public": False,
        "total_funding": 540_000_000,
    },
    {
        "name": "Pika",
        "industry": "AI / Video Generation",
        "website": "https://pika.art",
        "description": "AI video generation startup. GPU-intensive model training and inference.",
        "hq_location": "Palo Alto, CA",
        "employee_count": 80,
        "is_public": False,
        "total_funding": 135_000_000,
    },
    {
        "name": "Suno AI",
        "industry": "AI / Music Generation",
        "website": "https://suno.com",
        "description": "AI music generation platform. Scaling inference for consumer product.",
        "hq_location": "Cambridge, MA",
        "employee_count": 60,
        "is_public": False,
        "total_funding": 125_000_000,
    },
    # --- Enterprise AI / Large Companies Expanding AI Infra ---
    {
        "name": "Palantir Technologies",
        "industry": "Enterprise AI / Data Analytics",
        "website": "https://palantir.com",
        "description": "Enterprise AI platform. AIP driving massive demand for inference compute.",
        "hq_location": "Denver, CO",
        "employee_count": 4000,
        "is_public": True,
        "ticker": "PLTR",
    },
    {
        "name": "Snowflake",
        "industry": "Data / AI Platform",
        "website": "https://snowflake.com",
        "description": "Cloud data platform expanding heavily into AI/ML workloads via Cortex.",
        "hq_location": "Bozeman, MT",
        "employee_count": 6500,
        "is_public": True,
        "ticker": "SNOW",
    },
    {
        "name": "ServiceNow",
        "industry": "Enterprise Software / AI",
        "website": "https://servicenow.com",
        "description": "Enterprise workflow platform investing heavily in AI agents. Building own models.",
        "hq_location": "Santa Clara, CA",
        "employee_count": 22000,
        "is_public": True,
        "ticker": "NOW",
    },
    {
        "name": "Salesforce",
        "industry": "Enterprise Software / AI",
        "website": "https://salesforce.com",
        "description": "CRM giant investing in Einstein AI and Agentforce. Large inference compute needs.",
        "hq_location": "San Francisco, CA",
        "employee_count": 73000,
        "is_public": True,
        "ticker": "CRM",
    },
    {
        "name": "SAP",
        "industry": "Enterprise Software / AI",
        "website": "https://sap.com",
        "description": "Enterprise software giant embedding AI across products. Building Joule AI copilot.",
        "hq_location": "Walldorf, Germany",
        "employee_count": 107000,
        "is_public": True,
        "ticker": "SAP",
    },
    {
        "name": "Oracle",
        "industry": "Cloud / Enterprise / AI",
        "website": "https://oracle.com",
        "description": "Rapidly expanding cloud infrastructure for AI. OCI GPU offerings growing fast.",
        "hq_location": "Austin, TX",
        "employee_count": 160000,
        "is_public": True,
        "ticker": "ORCL",
    },
    {
        "name": "Tesla",
        "industry": "Automotive / AI / Robotics",
        "website": "https://tesla.com",
        "description": "Building Dojo supercomputer for FSD training. Massive and growing GPU needs.",
        "hq_location": "Austin, TX",
        "employee_count": 140000,
        "is_public": True,
        "ticker": "TSLA",
    },
    {
        "name": "Apple",
        "industry": "Technology / AI",
        "website": "https://apple.com",
        "description": "Building Apple Intelligence. Expanding server-side AI inference infrastructure.",
        "hq_location": "Cupertino, CA",
        "employee_count": 164000,
        "is_public": True,
        "ticker": "AAPL",
    },
    # --- Hyperscalers Needing Overflow Capacity ---
    {
        "name": "Microsoft",
        "industry": "Cloud / AI",
        "website": "https://microsoft.com",
        "description": "Azure AI and OpenAI partnership driving massive DC expansion. Already an Iren customer.",
        "hq_location": "Redmond, WA",
        "employee_count": 228000,
        "is_public": True,
        "ticker": "MSFT",
    },
    {
        "name": "Meta Platforms",
        "industry": "Social Media / AI",
        "website": "https://meta.com",
        "description": "Building Llama models and AI infrastructure. One of the largest GPU buyers globally.",
        "hq_location": "Menlo Park, CA",
        "employee_count": 72000,
        "is_public": True,
        "ticker": "META",
    },
    # --- Government / Research ---
    {
        "name": "Booz Allen Hamilton",
        "industry": "Government Consulting / AI",
        "website": "https://boozallen.com",
        "description": "Major government IT contractor with growing AI practice for defense/intel agencies.",
        "hq_location": "McLean, VA",
        "employee_count": 35000,
        "is_public": True,
        "ticker": "BAH",
    },
    {
        "name": "Leidos",
        "industry": "Defense / AI",
        "website": "https://leidos.com",
        "description": "Defense and IT services contractor expanding AI capabilities for government customers.",
        "hq_location": "Reston, VA",
        "employee_count": 47000,
        "is_public": True,
        "ticker": "LDOS",
    },
]

COMPETITORS = [
    # --- Neoclouds ---
    {
        "name": "CoreWeave",
        "industry": "GPU Cloud / Neocloud",
        "website": "https://coreweave.com",
        "description": "Leading neocloud. Strong NVIDIA partnership. Major contracts with Microsoft, OpenAI.",
        "hq_location": "Roseland, NJ",
        "is_public": True,
        "ticker": "CRWV",
        "capacity_mw": 1500,
        "gpu_count": 250000,
    },
    {
        "name": "Crusoe Energy",
        "industry": "AI Cloud / Energy",
        "website": "https://crusoe.ai",
        "description": "Vertically integrated AI cloud with ~3.4 GW power pipeline. Direct Iren competitor model.",
        "hq_location": "San Francisco, CA",
        "is_public": False,
        "capacity_mw": 600,
        "gpu_count": 200000,
    },
    {
        "name": "Lambda Labs",
        "industry": "GPU Cloud",
        "website": "https://lambdalabs.com",
        "description": "Developer-focused GPU cloud. Strong brand with ML researchers.",
        "hq_location": "San Francisco, CA",
        "is_public": False,
        "capacity_mw": 200,
        "gpu_count": 30000,
    },
    {
        "name": "Nebius",
        "industry": "AI Cloud",
        "website": "https://nebius.com",
        "description": "European-focused AI cloud (Yandex spin-off). Data sovereignty play.",
        "hq_location": "Amsterdam, Netherlands",
        "is_public": True,
        "ticker": "NBIS",
        "capacity_mw": 300,
    },
    {
        "name": "Voltage Park",
        "industry": "GPU Cloud",
        "website": "https://voltagepark.com",
        "description": "GPU cloud offering H100 clusters at competitive prices.",
        "hq_location": "San Francisco, CA",
        "is_public": False,
        "capacity_mw": 100,
    },
    # --- Hyperscaler Cloud (Competitors for GPU workloads) ---
    {
        "name": "Amazon Web Services",
        "industry": "Cloud / Hyperscaler",
        "website": "https://aws.amazon.com",
        "description": "Largest cloud provider. Expanding GPU offerings with Trainium chips and NVIDIA instances.",
        "hq_location": "Seattle, WA",
        "is_public": True,
        "ticker": "AMZN",
    },
    {
        "name": "Google Cloud",
        "industry": "Cloud / Hyperscaler",
        "website": "https://cloud.google.com",
        "description": "Major cloud provider with TPU and GPU offerings. A]2 A3 GPU instances.",
        "hq_location": "Mountain View, CA",
        "is_public": True,
        "ticker": "GOOGL",
    },
    # --- Traditional Data Center REITs ---
    {
        "name": "Equinix",
        "industry": "Data Center REIT",
        "website": "https://equinix.com",
        "description": "Largest data center REIT globally. Expanding into AI/HPC colocation.",
        "hq_location": "Redwood City, CA",
        "is_public": True,
        "ticker": "EQIX",
        "capacity_mw": 3000,
    },
    {
        "name": "Digital Realty",
        "industry": "Data Center REIT",
        "website": "https://digitalrealty.com",
        "description": "Second-largest DC REIT. Building high-density AI-ready facilities.",
        "hq_location": "Austin, TX",
        "is_public": True,
        "ticker": "DLR",
        "capacity_mw": 2500,
    },
    {
        "name": "QTS Realty (Blackstone)",
        "industry": "Data Center",
        "website": "https://qtsdatacenters.com",
        "description": "Large-scale data centers owned by Blackstone. Hyperscale campus model.",
        "hq_location": "Ashburn, VA",
        "is_public": False,
        "capacity_mw": 2000,
    },
    {
        "name": "CyrusOne (KKR)",
        "industry": "Data Center",
        "website": "https://cyrusone.com",
        "description": "Enterprise-focused data center provider owned by KKR.",
        "hq_location": "Dallas, TX",
        "is_public": False,
        "capacity_mw": 1000,
    },
    {
        "name": "Vantage Data Centers",
        "industry": "Data Center",
        "website": "https://vantage-dc.com",
        "description": "Hyperscale data center developer with campuses across North America, EMEA, APAC.",
        "hq_location": "Denver, CO",
        "is_public": False,
        "capacity_mw": 2500,
    },
    # --- Power-First / Energy Players ---
    {
        "name": "Lancium",
        "industry": "Energy / Data Center",
        "website": "https://lancium.com",
        "description": "Texas-based clean energy DC developer. Direct competitor on power-first model.",
        "hq_location": "Houston, TX",
        "is_public": False,
        "capacity_mw": 2000,
    },
    {
        "name": "Applied Digital",
        "industry": "AI Data Center",
        "website": "https://applieddigital.com",
        "description": "AI data center company in North Dakota and Texas. Building for AI/HPC workloads.",
        "hq_location": "Dallas, TX",
        "is_public": True,
        "ticker": "APLD",
        "capacity_mw": 600,
    },
    # --- International ---
    {
        "name": "Adani Group",
        "industry": "Conglomerate / Data Center",
        "website": "https://adani.com",
        "description": "Indian conglomerate planning ~5 GW of AI data centers by 2028.",
        "hq_location": "Ahmedabad, India",
        "is_public": True,
        "ticker": "ADANIENT.NS",
        "capacity_mw": 500,
    },
]


def seed_database():
    """Insert initial companies if database is empty."""
    init_db()
    session = get_session()

    existing = session.query(Company).count()
    if existing > 0:
        print(f"Database already has {existing} companies — skipping seed.")
        session.close()
        return

    count = 0
    for data in PROSPECTS:
        company = Company(company_type="prospect", **data)
        session.add(company)
        count += 1

    for data in COMPETITORS:
        company = Company(company_type="competitor", **data)
        session.add(company)
        count += 1

    session.commit()
    print(f"Seeded {count} companies ({len(PROSPECTS)} prospects, {len(COMPETITORS)} competitors).")
    session.close()


if __name__ == "__main__":
    seed_database()
