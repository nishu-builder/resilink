"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import Image from 'next/image';

export function Header() {
  const pathname = usePathname();

  const navItems = [
    { href: '/datasets/hazards', label: 'Hazard Datasets' },
    { href: '/datasets/buildings', label: 'Building Datasets' },
    { href: '/datasets/fragilities', label: 'Fragility Datasets' },
    { href: '/datasets/mappings', label: 'Mapping Datasets' },
    { href: '/runs', label: 'Runs' },
    { href: '/run-groups', label: 'Run Groups' },
  ];

  return (
    <header className="border-b">
      <div className="container mx-auto flex h-14 items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 text-xl font-semibold">
          {/* Logo placeholder - replace with actual logo once provided */}
        <Image
          src="/resilink-logo-small.png"
          alt="Resilink Logo"
          width={32}
          height={32}
          className="w-8 h-8"
        />
          <span>Resilink</span>
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