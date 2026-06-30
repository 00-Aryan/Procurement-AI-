import {
  BarChart3,
  Boxes,
  Bot,
  FileText,
  Home,
  Lightbulb,
  PackageCheck,
  Rocket,
  Search,
  ShieldAlert,
  TrendingUp,
  UploadCloud,
  UsersRound
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import industryConfig from "../../../industry-config.json";

type NodeType = {
  abstract_id: string;
  domain_label: string;
  domain_plural: string;
  role: string;
};

const nodeTypes = industryConfig.entity_mapping.node_types as NodeType[];
const buyerNode = nodeTypes.find((node) => node.abstract_id === "node.buyer");
const sellerNode = nodeTypes.find((node) => node.abstract_id === "node.seller");
const flowType = industryConfig.entity_mapping.flow_types[0];
const thresholds = industryConfig.risk_engine.band_thresholds;

export type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  comingSoon?: boolean;
};

export const tenantProfile = industryConfig.tenant_profile;

export const navItems: NavItem[] = [
  { label: "Home", href: "/", icon: Home },
  { label: "Demand Forecast", href: "/forecast", icon: TrendingUp, comingSoon: true },
  { label: "Inventory Intelligence", href: "/inventory", icon: Boxes },
  { label: "Supplier Intelligence", href: "/suppliers", icon: UsersRound, comingSoon: true },
  { label: "Risk & Anomalies", href: "/anomalies", icon: ShieldAlert },
  { label: "Recommendations", href: "/recommendations", icon: Lightbulb },
  { label: "Reports", href: "/reports", icon: FileText },
  { label: "AI Copilot", href: "/copilot", icon: Bot }
];

export type InsightCard = {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
  comingSoon?: boolean;
};

export const insightCards: InsightCard[] = [
  {
    title: "Demand Forecast",
    description: `Predict future ${flowType.domain_plural.toLowerCase()} and plan purchases with confidence.`,
    href: "/forecast",
    icon: TrendingUp,
    comingSoon: true
  },
  {
    title: "Inventory Intelligence",
    description: "Track inventory health and identify stock risks in real time.",
    href: "/inventory",
    icon: PackageCheck
  },
  {
    title: "Supplier Intelligence",
    description: `Evaluate ${sellerNode?.domain_plural.toLowerCase() ?? "supplier"} performance and reliability.`,
    href: "/suppliers",
    icon: UsersRound,
    comingSoon: true
  },
  {
    title: "Risk & Anomalies",
    description: `Detect anomalies and mitigate ${flowType.domain_label.toLowerCase()} risks early.`,
    href: "/anomalies",
    icon: ShieldAlert
  },
  {
    title: "Recommendations",
    description: "Get AI-powered recommendations to optimize decisions.",
    href: "/recommendations",
    icon: Lightbulb
  },
  {
    title: "Reports",
    description: "View and download insightful reports and analytics.",
    href: "/reports",
    icon: FileText
  }
];

export const dashboardMetrics = [
  { label: "Active Tenant", value: tenantProfile.tenant_name, detail: tenantProfile.tier },
  { label: "Primary Flow", value: flowType.domain_label, detail: `${flowType.max_concurrency} max concurrency` },
  { label: "Responder Node", value: sellerNode?.domain_plural ?? "Responders", detail: sellerNode?.role ?? "responder" },
  { label: "Critical Risk", value: `${Math.round(thresholds.critical * 100)}%`, detail: "configured threshold" }
];

export const gettingStartedSteps = [
  { title: "Getting Started", detail: `Upload ${buyerNode?.domain_plural.toLowerCase() ?? "entity"} data to unlock insights.`, icon: Rocket },
  { title: "1. Upload Data", detail: "Import procurement, inventory and supplier data.", icon: UploadCloud },
  { title: "2. We Analyze", detail: "Models process tenant-scoped signals.", icon: Search },
  { title: "3. Get Insights", detail: "Explore dashboards, reports and actions.", icon: BarChart3 }
];
