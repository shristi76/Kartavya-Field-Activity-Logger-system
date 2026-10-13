
export interface FieldReport {
  worker_name: string | null;
  date: string | null;

  location: string | null;
  organization: string | null;
  village: string | null;
  block: string | null;
  district: string | null;

  activity: string | null;

  people_visited: number | null;
  households_visited: number | null;
  beneficiaries_assisted: number | null;

  issues_identified: string | null;
  education_related_issues: string | null;
  health_and_wellbeing_concerns: string | null;
  family_and_child_welfare_concerns: string | null;
  livelihood_and_financial_issues: string | null;
  government_scheme_and_benefit_issues: string | null;
  elderly_and_disability_support_needs: string | null;

  assistance_provided: string | null;
  actions_taken: string | null;
  referrals_made: string | null;
  services_or_benefits_accessed: string | null;
  referral_required: string | null;

  follow_up_required: string | null;
  follow_up_date: string | null;
  responsible_person: string | null;

  outcomes_and_progress: string | null;
  translated_text: string | null;
  additional_notes: string | null;
}

export interface ReportResponse {
  success: boolean;
  message?: string;
  report: FieldReport;
  pdf_url?: string | null;
}
