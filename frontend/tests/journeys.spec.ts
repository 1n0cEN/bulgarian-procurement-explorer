import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {mkdirSync} from 'node:fs';

test('home reconciles and search navigates through detail and provenance',async({page})=>{
 await page.goto('/');
 await expect(page.getByText('5,367,011.18 BGN')).toBeVisible();
 await page.getByRole('link',{name:'View all contracts'}).click();
 await expect(page.getByText('11 matching contracts')).toBeVisible();
 await page.locator('.record-title').first().click();
 await expect(page.getByRole('heading',{name:'Source & provenance'})).toBeVisible();
 await expect(page.getByRole('link',{name:'Open original TED notice'})).toHaveAttribute('href',/^https:\/\/ted\.europa\.eu\/bg\/notice\/-\/detail\/\d+-2023$/);
 await page.getByText(/TED .*published/).click();
 await expect(page.getByText('ted-f03-1.0.0')).toBeVisible();
 await page.getByRole('link',{name:'View procurement and all award outcomes'}).click();
 await expect(page.getByRole('heading',{name:'Award outcomes'})).toBeVisible();
});

test('filters, no results, shares, comparisons and CSV export',async({page})=>{
 await page.goto('/search');
 await expect(page.getByText('11 matching contracts')).toBeVisible();
 await page.getByLabel('Currency',{exact:true}).selectOption('BGN');
 await page.getByLabel('Minimum value').fill('4000000');
 await page.getByRole('button',{name:'Apply filters'}).click();
 await expect(page.getByText('1 matching contracts')).toBeVisible();
 const downloadPromise=page.waitForEvent('download');
 await page.getByRole('link',{name:'Download CSV'}).click();
 const download=await downloadPromise;expect(download.suggestedFilename()).toBe('bg-award-values.csv');
 await page.goto('/search?q=no-such-record-xyz');
 await expect(page.getByRole('heading',{name:'No matching contracts'})).toBeVisible();
 await page.goto('/organizations');await page.locator('.directory a').first().click();
 await expect(page.getByRole('heading',{name:'Sole-supplier value shares'})).toBeVisible();
 await page.goto('/suppliers');await page.locator('.directory a').first().click();
 await expect(page.getByRole('heading',{name:'Indexed contracts'})).toBeVisible();
 await page.goto('/compare');await page.getByLabel('Authority A').selectOption({index:1});await page.getByLabel('Authority B').selectOption({index:2});
 await expect(page.getByRole('link',{name:'Inspect underlying records'})).toHaveCount(2);
});

test('accessibility, keyboard, responsive layout and screenshots',async({page})=>{
 mkdirSync('../docs/screenshots',{recursive:true});
 for(const route of ['/','/search','/organizations','/suppliers','/compare','/methodology','/sources']){
  await page.goto(route);await page.waitForLoadState('networkidle');
  const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
  expect(results.violations,JSON.stringify(results.violations)).toEqual([]);
 }
 await page.goto('/');await page.waitForLoadState('networkidle');
 await page.keyboard.press('Tab');await expect(page.getByRole('link',{name:'Skip to content'})).toBeFocused();
 await page.screenshot({path:'../docs/screenshots/home-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:'../docs/screenshots/home-mobile.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.goto('/search');await page.waitForLoadState('networkidle');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});

test('source unavailable is explained instead of showing fabricated data',async({page})=>{
 await page.route('**/api/v1/contracts?**',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Data temporarily unavailable'})}));
 await page.goto('/search');await expect(page.getByRole('heading',{name:'We couldn’t load these records.'})).toBeVisible();
});
