import Image from 'next/image';
export default function Home() {
  return (
    <section className="py-16 text-center">
      <div className="max-w-4xl mx-auto">
        {/* Logo placeholder - replace with actual logo once provided */}
   <div className="w-20 h-20 flex items-center justify-center mx-auto mb-6">
     <Image
       src="/resilink-logo-small.png"
       alt="Resilink Logo"
       width={80}
       height={80}
       className="w-20 h-20"
     />
   </div>
        <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-teal-600 bg-clip-text text-transparent">
          Resilink
        </h1>
        <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
          Advanced flood resilience analysis and damage assessment platform for communities and infrastructure.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
          <div className="p-6 border rounded-lg">
            <h3 className="font-semibold mb-2">Dataset Management</h3>
            <p className="text-sm text-muted-foreground">Upload and manage hazard, building, and fragility datasets</p>
          </div>
          <div className="p-6 border rounded-lg">
            <h3 className="font-semibold mb-2">Analysis Runs</h3>
            <p className="text-sm text-muted-foreground">Execute flood damage analysis with customizable parameters</p>
          </div>
          <div className="p-6 border rounded-lg">
            <h3 className="font-semibold mb-2">Results Visualization</h3>
            <p className="text-sm text-muted-foreground">Interactive maps and reports for decision making</p>
          </div>
        </div>
      </div>
    </section>
  );
} 