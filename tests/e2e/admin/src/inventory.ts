import fs from 'fs';
import path from 'path';
import type { AdminInventory, AdminModel } from './types';

// ADMIN_INVENTORY lets the suite run against a second stack (e.g. the vendor
// fork on :8001) without clobbering this tree's inventory.
const INVENTORY_PATH =
  process.env.ADMIN_INVENTORY ?? path.join(__dirname, '..', '.data', 'admin-inventory.json');

let cached: AdminInventory | null = null;

export function loadInventory(): AdminInventory {
  if (cached) return cached;
  if (!fs.existsSync(INVENTORY_PATH)) {
    throw new Error(
      `Admin inventory missing at ${INVENTORY_PATH}.\n` +
        'Generate it first:\n' +
        '  ./tests/e2e/admin/prepare.sh\n' +
        'or point ADMIN_INVENTORY at an inventory dumped from another stack.',
    );
  }
  cached = JSON.parse(fs.readFileSync(INVENTORY_PATH, 'utf8')) as AdminInventory;
  return cached;
}

export function models(): AdminModel[] {
  return loadInventory().models;
}

export function modelByLabel(label: string): AdminModel {
  const found = models().find((entry) => entry.label.toLowerCase() === label.toLowerCase());
  if (!found) throw new Error(`No admin registered for ${label}`);
  return found;
}

/**
 * Every URL the inventory says should exist. The crawl in 02 is checked against
 * this set so "we visited everything" is demonstrable rather than asserted.
 */
export function inventoryUrls(): string[] {
  const inventory = loadInventory();
  const urls = new Set<string>([
    inventory.admin_index,
    inventory.password_change,
  ]);

  for (const model of inventory.models) {
    for (const [kind, url] of Object.entries(model.urls)) {
      // The autocomplete endpoint is an AJAX API, not a page; delete pages are
      // destructive and belong to spec 06.
      if (!url || kind === 'autocomplete' || kind === 'delete') continue;
      urls.add(url);
    }
  }
  return [...urls].sort();
}
