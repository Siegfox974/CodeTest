import './globals.css';
import Navbar from '@/components/Navbar';

export const metadata = {
  title: 'InvestAI - Financial Dashboard',
  description: 'Professional financial investment dashboard with real-time market data',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-white min-h-screen">
        <Navbar />
        <main className="pt-16">{children}</main>
      </body>
    </html>
  );
}
