import './globals.css';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { ThemeProvider } from '@/app/context/theme-provider';
import { Header } from '@/app/components/header';
import "leaflet/dist/leaflet.css";

export const metadata: Metadata = {
  title: 'Hazard Explore',
  description: 'Flood hazard damage explorer',
};

const inter = Inter({ subsets: ['latin'] });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <Header />
          <div className="flex flex-col min-h-screen">
            <main className="flex-1 container mx-auto p-4">{children}</main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
} 