"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export function Header() {
  const pathname = usePathname();

  const navItems = [
    { href: '/datasets/hazards', label: 'Hazard Datasets' },
    { href: '/datasets/buildings', label: 'Building Datasets' },
    { href: '/datasets/fragilities', label: 'Fragility Datasets' },
    { href: '/datasets/mappings', label: 'Mapping Datasets' },
    { href: '/runs', label: 'Runs' },
  ];

  return (
    <header className="border-b">
      <div className="container mx-auto flex h-14 items-center justify-between px-4">
        <Link href="/" className="text-xl font-semibold">
          Hazard
        </Link>
        <nav className="flex gap-6">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`text-sm font-medium ${pathname?.startsWith(item.href) ? 'text-primary' : 'text-muted-foreground'}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
} 