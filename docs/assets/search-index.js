// Static search index for the docs site -- no server, no build step.
// Each entry: page (file), title (heading text), section (parent page title).
const SEARCH_INDEX = [
  { page: "index.html", title: "Django Forge", section: "Home", desc: "Overview and quick links" },
  { page: "index.html#why-forge", title: "Why Forge", section: "Home", desc: "The boilerplate problem this solves" },
  { page: "index.html#how-it-works", title: "How it works", section: "Home", desc: "Define, generate, ship" },
  { page: "index.html#principles", title: "Principles", section: "Home", desc: "Wrap don't reinvent, fails closed, no black box" },

  { page: "getting-started.html", title: "Getting started", section: "Guides", desc: "Install, define a Resource, generate an API" },
  { page: "getting-started.html#install", title: "Install into a project", section: "Getting started" },
  { page: "getting-started.html#define-resource", title: "Define a model and a Resource", section: "Getting started" },
  { page: "getting-started.html#generate", title: "Generate everything", section: "Getting started" },
  { page: "getting-started.html#wire-urls", title: "Wire the URLs", section: "Getting started" },
  { page: "getting-started.html#force", title: "Regenerating with --force", section: "Getting started" },

  { page: "resources.html", title: "The Resource class", section: "Core concepts", desc: "Fields, mixins, and what gets generated" },
  { page: "resources.html#fields", title: "fields, read_only_fields, searchable, filters, sortable", section: "The Resource class" },
  { page: "resources.html#generated-files", title: "What gets generated", section: "The Resource class" },
  { page: "resources.html#mixins", title: "Mixins", section: "The Resource class" },
  { page: "resources.html#soft-delete", title: "SoftDeleteViewSetMixin", section: "Mixins" },
  { page: "resources.html#owner-scoped", title: "OwnerScopedViewSetMixin", section: "Mixins" },
  { page: "resources.html#timestamped", title: "TimestampedSerializerMixin", section: "Mixins" },
  { page: "resources.html#multi-resource", title: "Multiple Resources in one app", section: "The Resource class" },

  { page: "rbac.html", title: "RBAC", section: "Core concepts", desc: "Roles, permissions, fail-closed enforcement" },
  { page: "rbac.html#permissions-map", title: "The permissions map", section: "RBAC" },
  { page: "rbac.html#roles", title: "Roles = Django Groups", section: "RBAC" },
  { page: "rbac.html#fail-closed", title: "Fails closed by default", section: "RBAC" },
  { page: "rbac.html#generated-tests", title: "Auto-generated permission tests", section: "RBAC" },

  { page: "tenancy.html", title: "Multi-tenancy", section: "Core concepts", desc: "Shared-schema organizations, fail-closed scoping" },
  { page: "tenancy.html#tenant-scoped-model", title: "TenantScopedModel", section: "Multi-tenancy" },
  { page: "tenancy.html#resolution", title: "How the current organization is resolved", section: "Multi-tenancy" },
  { page: "tenancy.html#admin", title: "Django admin sees every organization", section: "Multi-tenancy" },
  { page: "tenancy.html#composition", title: "RBAC + tenancy composition", section: "Multi-tenancy" },

  { page: "ai-engine.html", title: "AI engine", section: "Core concepts", desc: "Analyze + suggest, apply only with approval" },
  { page: "ai-engine.html#usage", title: "forge ai usage", section: "AI engine" },
  { page: "ai-engine.html#apply", title: "--apply", section: "AI engine", desc: "Approve and write files without leaving the terminal" },
  { page: "ai-engine.html#providers", title: "Providers", section: "AI engine", desc: "Anthropic, OpenAI, Gemini, Static" },
  { page: "ai-engine.html#providers", title: "OpenAIProvider, GeminiProvider", section: "AI engine" },
  { page: "ai-engine.html#providers", title: "Custom providers", section: "AI engine" },
  { page: "ai-engine.html#applying", title: "Applying the diff by hand", section: "AI engine" },

  { page: "audit-and-doctor.html", title: "Audit history & forge doctor", section: "Core concepts", desc: "Change history and project health checks" },
  { page: "audit-and-doctor.html#audit", title: "Audit history", section: "Audit history & forge doctor" },
  { page: "audit-and-doctor.html#doctor", title: "forge doctor checks", section: "Audit history & forge doctor" },

  { page: "demo.html", title: "Demo project", section: "Guides", desc: "Run the full example with seed data" },
  { page: "demo.html#resources", title: "The three demo Resources", section: "Demo project" },
  { page: "demo.html#seed", title: "seed_demo", section: "Demo project" },
  { page: "demo.html#accounts", title: "Demo accounts", section: "Demo project" },
];
