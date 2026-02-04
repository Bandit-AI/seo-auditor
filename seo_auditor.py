#!/usr/bin/env python3
"""
SEO Auditor - Instant SEO analysis with actionable recommendations
By Bandit 🦝 | raccoons.work
"""

import argparse
import json
import re
import sys
from urllib.parse import urlparse
from collections import Counter

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Install dependencies: pip install requests beautifulsoup4")
    sys.exit(1)


class SEOAuditor:
    def __init__(self, url: str):
        self.url = url
        self.soup = None
        self.html = None
        self.issues = []
        self.warnings = []
        self.passed = []
        
    def fetch(self) -> bool:
        """Fetch the page content."""
        try:
            headers = {'User-Agent': 'SEO-Auditor/1.0 (raccoons.work)'}
            response = requests.get(self.url, headers=headers, timeout=10)
            response.raise_for_status()
            self.html = response.text
            self.soup = BeautifulSoup(self.html, 'html.parser')
            return True
        except Exception as e:
            self.issues.append(f"❌ Could not fetch page: {e}")
            return False
    
    def check_title(self) -> dict:
        """Check page title."""
        title = self.soup.find('title')
        if not title or not title.text.strip():
            self.issues.append("❌ Missing page title")
            return {"title": None, "length": 0}
        
        title_text = title.text.strip()
        length = len(title_text)
        
        if length < 30:
            self.warnings.append(f"⚠️ Title too short ({length} chars) - aim for 50-60")
        elif length > 60:
            self.warnings.append(f"⚠️ Title too long ({length} chars) - may be truncated in search results")
        else:
            self.passed.append(f"✅ Title length good ({length} chars)")
            
        return {"title": title_text, "length": length}
    
    def check_meta_description(self) -> dict:
        """Check meta description."""
        meta = self.soup.find('meta', attrs={'name': 'description'})
        if not meta or not meta.get('content', '').strip():
            self.issues.append("❌ Missing meta description")
            return {"description": None, "length": 0}
        
        desc = meta['content'].strip()
        length = len(desc)
        
        if length < 120:
            self.warnings.append(f"⚠️ Meta description too short ({length} chars) - aim for 150-160")
        elif length > 160:
            self.warnings.append(f"⚠️ Meta description too long ({length} chars) - will be truncated")
        else:
            self.passed.append(f"✅ Meta description length good ({length} chars)")
            
        return {"description": desc, "length": length}
    
    def check_headings(self) -> dict:
        """Check heading structure."""
        headings = {}
        for i in range(1, 7):
            tags = self.soup.find_all(f'h{i}')
            headings[f'h{i}'] = [tag.text.strip() for tag in tags]
        
        # Check H1
        h1_count = len(headings['h1'])
        if h1_count == 0:
            self.issues.append("❌ Missing H1 heading")
        elif h1_count > 1:
            self.warnings.append(f"⚠️ Multiple H1 tags ({h1_count}) - use only one per page")
        else:
            self.passed.append("✅ Single H1 heading present")
        
        # Check heading hierarchy
        has_h2 = len(headings['h2']) > 0
        has_h3 = len(headings['h3']) > 0
        
        if has_h3 and not has_h2:
            self.warnings.append("⚠️ H3 present without H2 - maintain heading hierarchy")
        
        return headings
    
    def check_images(self) -> dict:
        """Check image optimization."""
        images = self.soup.find_all('img')
        total = len(images)
        missing_alt = []
        empty_alt = []
        
        for img in images:
            src = img.get('src', 'unknown')
            alt = img.get('alt')
            if alt is None:
                missing_alt.append(src)
            elif alt.strip() == '':
                empty_alt.append(src)
        
        if missing_alt:
            self.issues.append(f"❌ {len(missing_alt)} images missing alt attribute")
        if empty_alt:
            self.warnings.append(f"⚠️ {len(empty_alt)} images have empty alt text")
        if not missing_alt and not empty_alt and total > 0:
            self.passed.append(f"✅ All {total} images have alt text")
            
        return {"total": total, "missing_alt": len(missing_alt), "empty_alt": len(empty_alt)}
    
    def check_links(self) -> dict:
        """Check internal and external links."""
        links = self.soup.find_all('a', href=True)
        parsed_url = urlparse(self.url)
        base_domain = parsed_url.netloc
        
        internal = []
        external = []
        broken_format = []
        
        for link in links:
            href = link['href']
            if href.startswith('#') or href.startswith('javascript:'):
                continue
            elif href.startswith('/') or href.startswith(self.url) or base_domain in href:
                internal.append(href)
            elif href.startswith('http'):
                external.append(href)
            elif not href.startswith('mailto:') and not href.startswith('tel:'):
                broken_format.append(href)
        
        if broken_format:
            self.warnings.append(f"⚠️ {len(broken_format)} links with unusual format")
        
        self.passed.append(f"✅ Found {len(internal)} internal, {len(external)} external links")
        
        return {"internal": len(internal), "external": len(external), "unusual": len(broken_format)}
    
    def check_mobile(self) -> dict:
        """Check mobile-friendliness indicators."""
        viewport = self.soup.find('meta', attrs={'name': 'viewport'})
        
        if not viewport:
            self.issues.append("❌ Missing viewport meta tag - page may not be mobile-friendly")
            return {"viewport": False}
        
        content = viewport.get('content', '')
        if 'width=device-width' in content:
            self.passed.append("✅ Viewport configured for mobile")
        else:
            self.warnings.append("⚠️ Viewport may not be optimally configured")
            
        return {"viewport": True, "content": content}
    
    def check_performance_hints(self) -> dict:
        """Check for common performance issues."""
        issues_found = []
        
        # Check for render-blocking resources
        scripts = self.soup.find_all('script', src=True)
        blocking_scripts = [s for s in scripts if not s.get('async') and not s.get('defer')]
        if len(blocking_scripts) > 3:
            self.warnings.append(f"⚠️ {len(blocking_scripts)} render-blocking scripts - consider async/defer")
            issues_found.append("blocking_scripts")
        
        # Check for inline styles (minor)
        inline_styles = self.soup.find_all(style=True)
        if len(inline_styles) > 10:
            self.warnings.append(f"⚠️ {len(inline_styles)} inline styles - consider external CSS")
            issues_found.append("inline_styles")
        
        # Check HTML size
        html_size = len(self.html) / 1024  # KB
        if html_size > 100:
            self.warnings.append(f"⚠️ Large HTML size ({html_size:.1f}KB) - consider optimization")
            issues_found.append("large_html")
        else:
            self.passed.append(f"✅ HTML size reasonable ({html_size:.1f}KB)")
            
        return {"blocking_scripts": len(blocking_scripts), "html_size_kb": round(html_size, 1)}
    
    def check_structured_data(self) -> dict:
        """Check for structured data."""
        scripts = self.soup.find_all('script', type='application/ld+json')
        
        if not scripts:
            self.warnings.append("⚠️ No structured data (JSON-LD) found - consider adding for rich results")
            return {"found": False, "count": 0}
        
        self.passed.append(f"✅ Found {len(scripts)} structured data blocks")
        return {"found": True, "count": len(scripts)}
    
    def check_canonical(self) -> dict:
        """Check canonical URL."""
        canonical = self.soup.find('link', rel='canonical')
        
        if not canonical:
            self.warnings.append("⚠️ No canonical URL set - may cause duplicate content issues")
            return {"found": False}
        
        self.passed.append("✅ Canonical URL present")
        return {"found": True, "url": canonical.get('href')}
    
    def check_social_tags(self) -> dict:
        """Check Open Graph and Twitter cards."""
        og_tags = self.soup.find_all('meta', property=re.compile(r'^og:'))
        twitter_tags = self.soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
        
        result = {"og": len(og_tags), "twitter": len(twitter_tags)}
        
        if not og_tags:
            self.warnings.append("⚠️ Missing Open Graph tags - social shares won't look good")
        else:
            self.passed.append(f"✅ Found {len(og_tags)} Open Graph tags")
            
        if not twitter_tags:
            self.warnings.append("⚠️ Missing Twitter Card tags")
        else:
            self.passed.append(f"✅ Found {len(twitter_tags)} Twitter Card tags")
            
        return result
    
    def generate_score(self) -> int:
        """Generate an overall SEO score."""
        # Start at 100, deduct for issues
        score = 100
        score -= len(self.issues) * 15  # Critical issues
        score -= len(self.warnings) * 5  # Warnings
        return max(0, min(100, score))
    
    def run_audit(self) -> dict:
        """Run the full SEO audit."""
        if not self.fetch():
            return {"success": False, "issues": self.issues}
        
        results = {
            "url": self.url,
            "title": self.check_title(),
            "meta_description": self.check_meta_description(),
            "headings": self.check_headings(),
            "images": self.check_images(),
            "links": self.check_links(),
            "mobile": self.check_mobile(),
            "performance": self.check_performance_hints(),
            "structured_data": self.check_structured_data(),
            "canonical": self.check_canonical(),
            "social": self.check_social_tags(),
        }
        
        results["score"] = self.generate_score()
        results["issues"] = self.issues
        results["warnings"] = self.warnings
        results["passed"] = self.passed
        results["success"] = True
        
        return results
    
    def print_report(self, results: dict):
        """Print a formatted report."""
        if not results.get("success"):
            print("❌ Audit failed")
            for issue in results.get("issues", []):
                print(f"  {issue}")
            return
        
        print(f"\n{'='*60}")
        print(f"🔍 SEO AUDIT REPORT")
        print(f"{'='*60}")
        print(f"URL: {results['url']}")
        print(f"Score: {results['score']}/100")
        print(f"{'='*60}\n")
        
        if results['issues']:
            print("❌ CRITICAL ISSUES")
            print("-" * 40)
            for issue in results['issues']:
                print(f"  {issue}")
            print()
        
        if results['warnings']:
            print("⚠️  WARNINGS")
            print("-" * 40)
            for warning in results['warnings']:
                print(f"  {warning}")
            print()
        
        if results['passed']:
            print("✅ PASSED CHECKS")
            print("-" * 40)
            for passed in results['passed']:
                print(f"  {passed}")
            print()
        
        # Summary
        print("📊 SUMMARY")
        print("-" * 40)
        print(f"  Title: {results['title']['title'][:50]}..." if results['title']['title'] else "  Title: None")
        print(f"  H1 tags: {len(results['headings']['h1'])}")
        print(f"  Images: {results['images']['total']} ({results['images']['missing_alt']} missing alt)")
        print(f"  Links: {results['links']['internal']} internal, {results['links']['external']} external")
        print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='SEO Auditor - Instant SEO analysis',
        epilog='By Bandit 🦝 | raccoons.work'
    )
    parser.add_argument('url', help='URL to audit')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    # Validate URL
    if not args.url.startswith('http'):
        args.url = 'https://' + args.url
    
    auditor = SEOAuditor(args.url)
    results = auditor.run_audit()
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        auditor.print_report(results)


if __name__ == '__main__':
    main()
