import { Nav } from "./components/Nav";
import { Hero } from "./components/Hero";
import { ProblemSection } from "./components/ProblemSection";
import { SolutionSection } from "./components/SolutionSection";
import { ProductsSection } from "./components/ProductsSection";
import { EcosystemSection } from "./components/EcosystemSection";
import { ReceiptsSection } from "./components/ReceiptsSection";
import { MarketSection } from "./components/MarketSection";
import { TractionSection } from "./components/TractionSection";
import { TeamSection } from "./components/TeamSection";
import { InvestSection } from "./components/InvestSection";
import { Footer } from "./components/Footer";

export default function Home() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <ProblemSection />
        <SolutionSection />
        <ProductsSection />
        <EcosystemSection />
        <ReceiptsSection />
        <MarketSection />
        <TractionSection />
        <TeamSection />
        <InvestSection />
      </main>
      <Footer />
    </>
  );
}
