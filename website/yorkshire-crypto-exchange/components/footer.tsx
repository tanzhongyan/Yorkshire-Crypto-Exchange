import React from "react";

export const DashboardFooter: React.FC = () => {
  return (
    <footer className="py-4 border-t bg-card text-card-foreground mt-auto">
      <div className="container mx-auto px-4">
        <div className="text-center text-sm text-muted-foreground">
          <p>© 2025 Tan Zhong Yan. All rights reserved.</p>
          <p className="mt-1">Infrastructure and ongoing development independently maintained by Tan Zhong Yan.</p>
        </div>
      </div>
    </footer>
  );
};

export default DashboardFooter;