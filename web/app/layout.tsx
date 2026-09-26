import "./style.css";
export const metadata = {
  title: "Rushh · Banc vocal",
  description: "Composez, écoutez et comparez vos agents vocaux.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
