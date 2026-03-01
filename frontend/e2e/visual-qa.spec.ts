import { expect, test, type Page } from "@playwright/test"

const TODAY = "2026-02-28T12:00:00Z"
const YESTERDAY = "2026-02-27T09:30:00Z"
const LAST_WEEK = "2026-02-21T14:00:00Z"

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_DASHBOARD: Record<string, unknown> = {
  kpis: {
    active_prospects: 12,
    pipeline_hot: 4,
    hot_prospects: [
      { id: 1, name: "CoreWeave", score: 87, tier: "VERY HIGH" },
      { id: 2, name: "Lambda Labs", score: 72, tier: "HIGH" },
      { id: 3, name: "Crusoe Energy", score: 65, tier: "HIGH" },
      { id: 4, name: "Applied Digital", score: 58, tier: "MEDIUM" },
    ],
    signals_7d: 23,
    signals_delta: 8,
    signal_breakdown: {
      fundraising: 5,
      funding_completed: 3,
      hiring: 7,
      ai_initiative: 4,
      cloud_spend: 2,
      outgrowing: 2,
    },
    hottest_mover: {
      name: "CoreWeave",
      id: 1,
      delta: 14,
      score: 87,
      top_signal_type: "funding_completed",
    },
  },
  call_list: [
    {
      id: 1,
      name: "CoreWeave",
      industry: "GPU Cloud / Neocloud",
      product_fit: "ai_cloud",
      score: 87,
      tier: "VERY HIGH",
      delta: 14,
      top_signal_type: "funding_completed",
      headline: "$7.5B Series C closes — massive GPU buildout imminent",
      action_insight: "Reach out within 2 weeks while budget is fresh",
      urgency: "high",
      primary_contact: {
        id: 1,
        name: "Mike Intrator",
        title: "CEO",
        role_type: "economic",
        seniority: "C-Suite",
        recommended_approach: "Executive briefing on Iren capacity",
        last_contacted: null,
      },
      score_breakdown: { fundraising: 10, funding_completed: 20, hiring: 18, ai_initiative: 15, cloud_spend: 12, outgrowing: 12 },
    },
    {
      id: 2,
      name: "Lambda Labs",
      industry: "AI Cloud",
      product_fit: "ai_cloud",
      score: 72,
      tier: "HIGH",
      delta: 6,
      top_signal_type: "hiring",
      headline: "Hiring 50+ DC engineers across 3 regions",
      action_insight: "Expansion signals — propose colocation partnership",
      urgency: "medium",
      primary_contact: {
        id: 2,
        name: "Stephen Balaban",
        title: "CEO & Co-Founder",
        role_type: "economic",
        seniority: "C-Suite",
        recommended_approach: "Technical demo of GPU-ready infrastructure",
        last_contacted: LAST_WEEK,
      },
      score_breakdown: { fundraising: 8, funding_completed: 5, hiring: 20, ai_initiative: 18, cloud_spend: 12, outgrowing: 9 },
    },
    {
      id: 3,
      name: "Crusoe Energy",
      industry: "Sustainable Cloud",
      product_fit: "colocation",
      score: 65,
      tier: "HIGH",
      delta: 3,
      top_signal_type: "ai_initiative",
      headline: "Announced carbon-negative AI cloud strategy",
      action_insight: "Align on sustainability narrative",
      urgency: "medium",
      primary_contact: null,
      score_breakdown: { fundraising: 12, funding_completed: 8, hiring: 10, ai_initiative: 18, cloud_spend: 10, outgrowing: 7 },
    },
  ],
  cooling: [
    { id: 5, name: "Cerebras", industry: "AI Chips", product_fit: "ai_cloud", score: 34, tier: "LOW", delta: -8, top_signal_type: null, score_breakdown: { fundraising: 5, funding_completed: 3, hiring: 8, ai_initiative: 10, cloud_spend: 5, outgrowing: 3 } },
    { id: 6, name: "Inflection AI", industry: "AI Lab", product_fit: "ai_cloud", score: 28, tier: "LOW", delta: -12, top_signal_type: null, score_breakdown: { fundraising: 4, funding_completed: 2, hiring: 6, ai_initiative: 8, cloud_spend: 5, outgrowing: 3 } },
  ],
  top_ranked: [
    { id: 1, name: "CoreWeave", industry: "GPU Cloud / Neocloud", product_fit: "ai_cloud", score: 87, tier: "VERY HIGH", delta: 14, top_signal_type: "funding_completed", score_breakdown: { fundraising: 10, funding_completed: 20, hiring: 18, ai_initiative: 15, cloud_spend: 12, outgrowing: 12 } },
    { id: 2, name: "Lambda Labs", industry: "AI Cloud", product_fit: "ai_cloud", score: 72, tier: "HIGH", delta: 6, top_signal_type: "hiring", score_breakdown: { fundraising: 8, funding_completed: 5, hiring: 20, ai_initiative: 18, cloud_spend: 12, outgrowing: 9 } },
    { id: 3, name: "Crusoe Energy", industry: "Sustainable Cloud", product_fit: "colocation", score: 65, tier: "HIGH", delta: 3, top_signal_type: "ai_initiative", score_breakdown: { fundraising: 12, funding_completed: 8, hiring: 10, ai_initiative: 18, cloud_spend: 10, outgrowing: 7 } },
  ],
  alerts: [
    { company_name: "CoreWeave", event_type: "expansion", title: "CoreWeave opens new 100MW campus in Dallas", detected_at: TODAY },
    { company_name: "Equinix", event_type: "pricing", title: "Equinix raises colocation prices 8% across NA", detected_at: YESTERDAY },
  ],
  competitive_pulse: {
    events_7d: 5,
    signals_7d: 12,
    most_active: "CoreWeave",
    most_active_count: 4,
    high_threat_count: 2,
  },
}

const MOCK_DIGEST = { digest: "This week saw a surge in GPU cloud funding. CoreWeave closed its $7.5B Series C, Lambda Labs is aggressively hiring DC engineers, and Crusoe announced a carbon-negative AI strategy. Equinix raised NA colo prices 8%. Recommend prioritizing CoreWeave and Lambda outreach.", period: "morning" }

const MOCK_PROSPECTS = [
  {
    id: 1, name: "CoreWeave", company_type: "prospect", industry: "GPU Cloud / Neocloud", website: "https://coreweave.com", description: "Leading GPU cloud provider", hq_location: "Roseland, NJ",
    employee_count: 1200, founded_year: 2017, is_public: true, ticker: "CRWV", product_fit: "ai_cloud", capacity_mw: 1500, gpu_count: 250000, known_pricing: null, total_funding: 12500000000, last_funding_amount: 7500000000,
    score: { total: 87, fundraising: 10, funding_completed: 20, hiring: 18, ai_initiative: 15, cloud_spend: 12, outgrowing: 12, scored_at: TODAY },
    delta: 14, tier: "VERY HIGH" as const, signals_7d: 5, top_signal_type: "funding_completed" as const,
  },
  {
    id: 2, name: "Lambda Labs", company_type: "prospect", industry: "AI Cloud", website: "https://lambdalabs.com", description: "AI cloud infrastructure", hq_location: "San Francisco, CA",
    employee_count: 300, founded_year: 2012, is_public: false, ticker: null, product_fit: "ai_cloud", capacity_mw: 200, gpu_count: 40000, known_pricing: null, total_funding: 800000000, last_funding_amount: 320000000,
    score: { total: 72, fundraising: 8, funding_completed: 5, hiring: 20, ai_initiative: 18, cloud_spend: 12, outgrowing: 9, scored_at: TODAY },
    delta: 6, tier: "HIGH" as const, signals_7d: 3, top_signal_type: "hiring" as const,
  },
  {
    id: 3, name: "Crusoe Energy", company_type: "prospect", industry: "Sustainable Cloud", website: "https://crusoe.ai", description: "Sustainable AI cloud", hq_location: "Denver, CO",
    employee_count: 500, founded_year: 2018, is_public: false, ticker: null, product_fit: "colocation", capacity_mw: 400, gpu_count: 20000, known_pricing: null, total_funding: 900000000, last_funding_amount: 500000000,
    score: { total: 65, fundraising: 12, funding_completed: 8, hiring: 10, ai_initiative: 18, cloud_spend: 10, outgrowing: 7, scored_at: TODAY },
    delta: 3, tier: "HIGH" as const, signals_7d: 2, top_signal_type: "ai_initiative" as const,
  },
  {
    id: 4, name: "Applied Digital", company_type: "prospect", industry: "Data Center", website: "https://applieddigital.com", description: "Next-gen data centers", hq_location: "Dallas, TX",
    employee_count: 150, founded_year: 2001, is_public: true, ticker: "APLD", product_fit: "build_to_suit", capacity_mw: 600, gpu_count: null, known_pricing: null, total_funding: null, last_funding_amount: null,
    score: { total: 58, fundraising: 6, funding_completed: 10, hiring: 12, ai_initiative: 10, cloud_spend: 12, outgrowing: 8, scored_at: TODAY },
    delta: -2, tier: "MEDIUM" as const, signals_7d: 1, top_signal_type: "cloud_spend" as const,
  },
  {
    id: 5, name: "Cerebras", company_type: "prospect", industry: "AI Chips", website: "https://cerebras.ai", description: "Wafer-scale AI computing", hq_location: "Sunnyvale, CA",
    employee_count: 400, founded_year: 2016, is_public: false, ticker: null, product_fit: "ai_cloud", capacity_mw: 100, gpu_count: null, known_pricing: null, total_funding: 720000000, last_funding_amount: 250000000,
    score: { total: 34, fundraising: 5, funding_completed: 3, hiring: 8, ai_initiative: 10, cloud_spend: 5, outgrowing: 3, scored_at: TODAY },
    delta: -8, tier: "LOW" as const, signals_7d: 0, top_signal_type: null,
  },
]

const MOCK_COMPETE = {
  iren: {
    name: "Iren", industry: "AI Data Center / Energy", capacity_mw: 1100, gpu_count: null, is_public: true, ticker: "IREN", hq_location: "Sydney, Australia", website: "https://iren.com", segment: "Data Center",
  },
  competitors: [
    {
      id: 10, name: "CoreWeave", company_type: "competitor", industry: "GPU Cloud / Neocloud", website: "https://coreweave.com", description: "Leading GPU cloud", hq_location: "Roseland, NJ",
      employee_count: 1200, is_public: true, ticker: "CRWV", capacity_mw: 1500, gpu_count: 250000, known_pricing: "~$2.50/hr H100", total_funding: 12500000000, score: null, delta: 0,
      segment: "Neocloud", signal_count_30d: 8, key_customers: ["Meta", "Microsoft"], strengths: ["Massive GPU fleet", "Kubernetes-native"], weaknesses: ["High burn rate", "Concentration risk"],
      threat_level: "high" as const, signals: [], events: [
        { id: 1, company_id: 10, event_type: "expansion", title: "New 100MW campus in Dallas", description: "CoreWeave expands footprint with Dallas campus targeting enterprise AI workloads.", source_url: "https://example.com/1", detected_at: TODAY },
      ],
    },
    {
      id: 11, name: "Equinix", company_type: "competitor", industry: "Data Center REIT", website: "https://equinix.com", description: "Largest data center REIT", hq_location: "Redwood City, CA",
      employee_count: 13000, is_public: true, ticker: "EQIX", capacity_mw: 3000, gpu_count: null, known_pricing: "$150-250/kW retail colo", total_funding: null, score: null, delta: 0,
      segment: "DC REIT", signal_count_30d: 3, key_customers: ["AWS", "Google Cloud", "Azure"], strengths: ["Global footprint", "Enterprise relationships"], weaknesses: ["Slow to adopt AI-specific infra", "Premium pricing"],
      threat_level: "medium" as const, signals: [], events: [
        { id: 2, company_id: 11, event_type: "pricing", title: "NA colocation prices raised 8%", description: "Equinix increases North American colocation pricing.", source_url: "https://example.com/2", detected_at: YESTERDAY },
      ],
    },
    {
      id: 12, name: "QTS Realty", company_type: "competitor", industry: "Data Center REIT", website: "https://qtsdatacenters.com", description: "Hyperscale data center provider", hq_location: "Overland Park, KS",
      employee_count: 800, is_public: false, ticker: null, capacity_mw: 2100, gpu_count: null, known_pricing: "$120-200/kW wholesale", total_funding: null, score: null, delta: 0,
      segment: "DC REIT", signal_count_30d: 1, key_customers: ["Meta", "Google"], strengths: ["Wholesale scale", "Land bank"], weaknesses: ["Limited AI specialization"],
      threat_level: "low" as const, signals: [], events: [],
    },
  ],
}

const MOCK_ADMIN = {
  companies: 15,
  signals: 247,
  scores: 12,
  briefs: 8,
  signal_distribution: { fundraising: 42, funding_completed: 28, hiring: 65, ai_initiative: 51, cloud_spend: 34, outgrowing: 27 },
  weights: {
    fundraising: { max_points: 15, base_points: 5, halflife: 60 },
    funding_completed: { max_points: 20, base_points: 8, halflife: 45 },
    hiring: { max_points: 20, base_points: 6, halflife: 30 },
    ai_initiative: { max_points: 18, base_points: 5, halflife: 45 },
    cloud_spend: { max_points: 15, base_points: 4, halflife: 60 },
    outgrowing: { max_points: 12, base_points: 4, halflife: 45 },
  },
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function mockAllAPIs(page: Page) {
  await page.route("**/api/dashboard", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_DASHBOARD) })
  )
  await page.route("**/api/dashboard/digest", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_DIGEST) })
  )
  await page.route("**/api/prospects", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_PROSPECTS) })
  )
  await page.route("**/api/competitors", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_COMPETE) })
  )
  await page.route("**/api/compete/landscape", (route) =>
    route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({ ...MOCK_COMPETE, segments: [], activity_feed: [] }),
    })
  )
  await page.route("**/api/signals**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) })
  )
  await page.route("**/api/admin/stats", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_ADMIN) })
  )
}

const SCREENSHOT_DIR = "e2e/screenshots"

// ---------------------------------------------------------------------------
// Visual QA — full-page screenshots of every route
// ---------------------------------------------------------------------------

test.describe("Visual QA", () => {
  test.beforeEach(async ({ page }) => {
    await mockAllAPIs(page)
  })

  test("Dashboard (/) — full page", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")
    await expect(page.locator("body")).toBeVisible()

    await expect(page.getByText("CoreWeave").first()).toBeVisible({ timeout: 10000 })

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/dashboard-full.png`,
      fullPage: true,
    })
  })

  test("Dashboard (/) — viewport only", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")
    await expect(page.getByText("CoreWeave").first()).toBeVisible({ timeout: 10000 })

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/dashboard-viewport.png`,
    })
  })

  test("Prospects (/prospects) — full page", async ({ page }) => {
    await page.goto("/prospects")
    await page.waitForLoadState("networkidle")
    await expect(page.locator("body")).toBeVisible()

    await expect(page.getByText("CoreWeave").first()).toBeVisible({ timeout: 10000 })

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/prospects-full.png`,
      fullPage: true,
    })
  })

  test("Compete (/compete) — full page", async ({ page }) => {
    await page.goto("/compete")
    await page.waitForLoadState("networkidle")
    await expect(page.locator("body")).toBeVisible()

    await expect(page.getByText("CoreWeave").first()).toBeVisible({ timeout: 10000 })

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/compete-full.png`,
      fullPage: true,
    })
  })

  test("Admin (/admin) — full page", async ({ page }) => {
    await page.goto("/admin")
    await page.waitForLoadState("networkidle")
    await expect(page.locator("body")).toBeVisible()

    await expect(page.getByText("247").first()).toBeVisible({ timeout: 10000 })

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/admin-full.png`,
      fullPage: true,
    })
  })

  test("Dashboard — wide viewport (1920x1080)", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto("/")
    await page.waitForLoadState("networkidle")
    await expect(page.getByText("CoreWeave").first()).toBeVisible({ timeout: 10000 })

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/dashboard-1920.png`,
    })
  })

  test("Dashboard — narrow viewport (768x1024)", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto("/")
    await page.waitForLoadState("networkidle")
    await expect(page.getByText("CoreWeave").first()).toBeVisible({ timeout: 10000 })

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/dashboard-768.png`,
    })
  })
})
