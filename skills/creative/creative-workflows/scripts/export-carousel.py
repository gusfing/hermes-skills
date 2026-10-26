#!/usr/bin/env python3
"""
Standalone Instagram Carousel HTML → PNG Exporter
Usage: python3 export-carousel.py carousel.html --output-dir slides_output
Requires: playwright (pip install playwright && python3 -m playwright install chromium)

This version matches the html-to-carousel tool's exact viewport scaling:
- 420×525 viewport with device_scale_factor=2.5714 (1080/420)
- Clips screenshots to 420×525, outputs 1080×1350 PNGs
"""
import argparse
import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

VIEW_W = 420
VIEW_H = 525
SCALE = 1080 / 420  # 2.5714
FONT_WAIT_MS = 3000

async def export_slides(html_path: Path, output_dir: Path, font_wait_ms: int):
    output_dir.mkdir(parents=True, exist_ok=True)
    html_content = html_path.read_text(encoding='utf-8')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": VIEW_W, "height": VIEW_H},
            device_scale_factor=SCALE,
        )
        
        # Load HTML
        await page.set_content(html_content, wait_until='networkidle')
        await page.wait_for_timeout(font_wait_ms)

        # Find .ig-frame (required by the original tool)
        ig_frame = await page.query_selector('.ig-frame')
        if not ig_frame:
            raise RuntimeError('Missing .ig-frame in the HTML file. Add <div class="ig-frame"> wrapping your carousel.')

        # Hide Instagram chrome elements
        await page.evaluate("""() => {
            document.querySelectorAll('.ig-header,.ig-dots,.ig-actions,.ig-caption')
                .forEach(el => el.style.display = 'none');
        }""")

        # Find slides
        slides = await page.query_selector_all('.carousel-track .slide')
        if not slides:
            slides = await page.query_selector_all('.slide')
        if not slides:
            raise RuntimeError('No .slide elements found inside .carousel-track or root')

        print(f'Exporting {len(slides)} slides...')
        
        for i, slide in enumerate(slides, 1):
            # For flex track layout, transform track to show this slide
            await page.evaluate("""({ index, width }) => {
                const track = document.querySelector('.carousel-track');
                if (track) {
                    track.style.transition = 'none';
                    track.style.transform = 'translateX(' + (-index * width) + 'px)';
                }
            }""", {"index": i - 1, "width": VIEW_W})
            await page.wait_for_timeout(400)
            
            # Screenshot clipped to viewport
            output_path = output_dir / f'{html_path.stem}_{i}.png'
            await page.screenshot(
                path=str(output_path),
                clip={"x": 0, "y": 0, "width": VIEW_W, "height": VIEW_H},
            )
            print(f'  Exported Slide {i}/{len(slides)}: {output_path.name}')

        await browser.close()
        print(f'Export complete! Folder: {output_dir}')

def main():
    parser = argparse.ArgumentParser(description='Export Instagram carousel slides from HTML to PNG (1080x1350)')
    parser.add_argument('html', help='Input HTML file')
    parser.add_argument('--output-dir', default='slides_output', help='Output directory (default: slides_output)')
    parser.add_argument('--font-wait-ms', type=int, default=FONT_WAIT_MS, help='Font load wait time (default: 3000)')
    args = parser.parse_args()

    html_path = Path(args.html)
    if not html_path.exists():
        sys.exit(f'HTML file not found: {html_path}')

    output_dir = Path(args.output_dir)
    
    try:
        asyncio.run(export_slides(html_path, output_dir, args.font_wait_ms))
    except Exception as e:
        sys.exit(f'Export failed: {e}')

if __name__ == '__main__':
    main()