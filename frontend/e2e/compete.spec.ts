import { expect, test } from "@playwright/test"

const MOCK_COMPETE_RESPONSE = {
  iren: {
    name: "Iren",
    industry: "AI Data Center / Energy",
    capacity_mw: 1100,
    gpu_count: null,
    is_public: true,
    ticker: "IREN",
    hq_location: "Sydney, Australia",
    website: "https://iren.com",
    segment: "Data Center",
  },
  competitors: [
    {
      id: 1,
      name: "CoreWeave",
      company_type: "competitor",
      industry: "GPU Cloud / Neocloud",
      website: "https://coreweave.com",
      description: "Leading neocloud.",
      hq_location: "Roseland, NJ",
      employee_count: null,
      is_public: true,
      ticker: "CRWV",
      capacity_mw: 1500,
      gpu_count: 250000,
      known_pricing: null,
      total_funding: null,
      score: null,
      delta: 0,
      segment: "Neocloud",
      signal_count_30d: 2,
      signals: [],
      events: [],
    },
    {
      id: 2,
      name: "Equinix",
      company_type: "competitor",
      industry: "Data Center REIT",
      website: "https://equinix.com",
      description: "Largest data center REIT.",
      hq_location: "Redwood City, CA",
      employee_count: null,
      is_public: true,
      ticker: "EQIX",
      capacity_mw: 3000,
      gpu_count: null,
      known_pricing: null,
      total_funding: null,
      score: null,
      delta: 0,
      segment: "DC REIT",
      signal_count_30d: 0,
      signals: [],
      events: [],
    },
  ],
}

test.describe("Compete page", () => {
  test("shows content when API returns competitors (mocked)", async ({ page }) => {
    await page.route("**/api/competitors**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_COMPETE_RESPONSE),
      })
    )

    await page.goto("/compete")

    await expect(page.getByRole("heading", { name: "Compete" })).toBeVisible()

    await expect(page.getByText("Competitors Tracked")).toBeVisible()
    await expect(page.getByText("2", { exact: true }).first()).toBeVisible()

    await expect(page.getByText("Iren Capacity Rank")).toBeVisible()
    await expect(page.getByText("Iren", { exact: true }).first()).toBeVisible()

    await expect(page.getByText("CoreWeave")).toBeVisible()
    await expect(page.getByText("Equinix")).toBeVisible()

    const table = page.locator("table")
    await expect(table).toBeVisible()
    await expect(table.getByRole("row")).toHaveCount(4)
  })

  test("shows structure when API returns empty competitors", async ({ page }) => {
    await page.route("**/api/competitors**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          iren: MOCK_COMPETE_RESPONSE.iren,
          competitors: [],
        }),
      })
    )

    await page.goto("/compete")

    await expect(page.getByRole("heading", { name: "Compete" })).toBeVisible()
    await expect(page.getByText("Competitors Tracked")).toBeVisible()
    await expect(page.getByText("Competitive landscape")).toBeVisible()

    await expect(page.getByText("Iren", { exact: true }).first()).toBeVisible()
    await expect(page.getByText("No competitors match this filter.")).toBeVisible()
  })

  test("shows loading then content or empty state", async ({ page }) => {
    await page.route("**/api/competitors**", async (route) => {
      await new Promise((r) => setTimeout(r, 100))
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_COMPETE_RESPONSE),
      })
    })

    await page.goto("/compete")

    await expect(page.getByRole("heading", { name: "Compete" })).toBeVisible({ timeout: 15000 })
    await expect(page.getByText("Competitors Tracked")).toBeVisible({ timeout: 5000 })
  })
})
