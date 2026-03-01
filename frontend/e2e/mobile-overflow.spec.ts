import { test, expect } from "@playwright/test"

// iPhone 17 approximate viewport (similar to iPhone 16 Pro)
const IPHONE_VIEWPORT = { width: 393, height: 852 }

const PAGES = [
  { name: "Dashboard", path: "/" },
  { name: "Prospects", path: "/prospects" },
  { name: "Compete", path: "/compete" },
  { name: "Admin", path: "/admin" },
]

test.describe("Mobile horizontal overflow check", () => {
  for (const page of PAGES) {
    test(`${page.name} - no horizontal overflow at iPhone width`, async ({ page: pw }) => {
      await pw.setViewportSize(IPHONE_VIEWPORT)
      await pw.goto(page.path, { waitUntil: "load" })
      await pw.waitForTimeout(1500)

      // Measure document scroll width vs viewport width
      const overflow = await pw.evaluate(() => {
        const docWidth = document.documentElement.scrollWidth
        const viewWidth = window.innerWidth
        const overflowingEls: { tag: string; id: string; class: string; scrollWidth: number; offsetWidth: number }[] = []

        // Walk the DOM and find elements wider than the viewport
        document.querySelectorAll("*").forEach((el) => {
          const htmlEl = el as HTMLElement
          if (htmlEl.scrollWidth > viewWidth + 2) {
            // +2px tolerance for rounding
            overflowingEls.push({
              tag: htmlEl.tagName,
              id: htmlEl.id,
              class: htmlEl.className?.toString().slice(0, 80),
              scrollWidth: htmlEl.scrollWidth,
              offsetWidth: htmlEl.offsetWidth,
            })
          }
        })

        return {
          docScrollWidth: docWidth,
          viewportWidth: viewWidth,
          hasOverflow: docWidth > viewWidth + 2,
          overflowingEls: overflowingEls.slice(0, 10),
        }
      })

      if (overflow.hasOverflow) {
        console.log(
          `\n${page.name}: doc=${overflow.docScrollWidth}px viewport=${overflow.viewportWidth}px\n` +
            `Overflowing elements:\n` +
            overflow.overflowingEls
              .map((e) => `  <${e.tag}> scrollWidth=${e.scrollWidth} class="${e.class}"`)
              .join("\n")
        )
      }

      await pw.screenshot({
        path: `e2e/screenshots/mobile-${page.name.toLowerCase()}.png`,
        fullPage: false,
      })

      expect(
        overflow.hasOverflow,
        `${page.name} has horizontal overflow. Overflowing elements:\n${overflow.overflowingEls.map((e) => `  <${e.tag}> scrollWidth=${e.scrollWidth} "${e.class}"`).join("\n")}`
      ).toBe(false)
    })
  }
})
