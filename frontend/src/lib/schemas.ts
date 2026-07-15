import { z } from "zod";

export const severitySchema = z.enum(["info", "watch", "elevated", "critical"]);

export const analysisSchema = z.object({
  job_id: z.string(),
  portfolio_id: z.string().nullable(),
  portfolio_version_id: z.string().nullable().optional(),
  portfolio_name: z.string().nullable().optional(),
  engine: z.string(),
  snapshot_id: z.string(),
  status: z.string(),
  portfolio_mean_p_impairment: z.number().nullable().optional(),
  macro_regime: z.string().nullable().optional(),
  stress_index: z.number().nullable().optional(),
  created_at: z.string(),
  finished_at: z.string().nullable().optional()
});

export const analysesResponseSchema = z.object({
  analyses: z.array(analysisSchema)
});

export const reportSummarySchema = z.object({
  report_id: z.string(),
  analysis_id: z.string(),
  engine: z.string(),
  headline: z.string(),
  action_count: z.number(),
  max_severity: severitySchema,
  portfolio_id: z.string().nullable().optional(),
  portfolio_name: z.string().nullable().optional(),
  created_at: z.string()
});

export const reportsResponseSchema = z.object({
  reports: z.array(reportSummarySchema)
});

export const citationSchema = z.object({
  artifact: z.string(),
  locator: z.string()
});

export const reportFigureSchema = z.object({
  label: z.string(),
  value: z.union([z.string(), z.number()]),
  severity: severitySchema,
  citation: citationSchema
});

export const reportActionSchema = z.object({
  title: z.string(),
  severity: severitySchema,
  rationale: z.string(),
  citations: z.array(citationSchema)
});

export const reportDetailSchema = z.object({
  report_id: z.string(),
  run_id: z.string(),
  engine: z.string(),
  snapshot_id: z.string(),
  engine_version: z.string().optional(),
  model_version: z.string().optional(),
  headline: z.string(),
  previous_run_id: z.string().nullable().optional(),
  key_figures: z.array(reportFigureSchema),
  risk_drivers: z.array(reportFigureSchema),
  actions: z.array(reportActionSchema)
});

export const portfolioCompanySchema = z.object({
  name: z.string(),
  ebitda: z.number(),
  multiple: z.number(),
  carrying_value: z.number()
});

export const portfolioSchema = z.object({
  portfolio_id: z.string(),
  name: z.string(),
  companies: z.array(portfolioCompanySchema).optional(),
  company_count: z.number().optional(),
  current_version_id: z.string().nullable().optional(),
  version_number: z.number().nullable().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional()
});

export const portfoliosResponseSchema = z.object({
  portfolios: z.array(portfolioSchema)
});

export const healthSchema = z.object({
  status: z.string().optional(),
  ok: z.boolean().optional(),
  version: z.string().optional()
}).passthrough();

export type Analysis = z.infer<typeof analysisSchema>;
export type ReportSummary = z.infer<typeof reportSummarySchema>;
export type ReportDetail = z.infer<typeof reportDetailSchema>;
export type Portfolio = z.infer<typeof portfolioSchema>;
export type Severity = z.infer<typeof severitySchema>;
