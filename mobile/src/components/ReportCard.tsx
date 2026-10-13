
import {
  StyleSheet,
  Text,
  View,
} from "react-native";

import { Colors } from "../constants/colors";
import { FieldReport } from "../types/report";

interface Props {
  report: FieldReport;
}

export default function ReportCard({ report }: Props) {
  return (
    <View style={styles.container}>
      {/* Report heading */}
      <View style={styles.header}>
        <View style={styles.icon}>
          <Text style={styles.iconText}>✓</Text>
        </View>

        <View style={styles.headerText}>
          <Text style={styles.eyebrow}>
            SOCIAL WORK FIELD REPORT
          </Text>

          <Text style={styles.title}>
            Field Visit Summary
          </Text>

          <Text style={styles.subtitle}>
            Generated from your voice recording
          </Text>
        </View>
      </View>

      {/* Location and worker information */}
      <SectionTitle
        title="Visit Information"
        subtitle="Worker, organization and location details"
      />

      <Info label="Social Worker" value={report.worker_name} />
      <Info label="Date" value={report.date} />
      <Info label="Organization" value={report.organization} />
      <Info label="Location" value={report.location} />
      <Info label="Village" value={report.village} />
      <Info label="Block" value={report.block} />
      <Info label="District" value={report.district} />

      {/* Visit statistics */}
      <SectionTitle
        title="People Reached"
        subtitle="Reported visit and assistance counts"
      />

      <View style={styles.statsContainer}>
        <StatCard
          label="People Visited"
          value={report.people_visited}
        />

        <StatCard
          label="Households"
          value={report.households_visited}
        />

        <StatCard
          label="Beneficiaries Assisted"
          value={report.beneficiaries_assisted}
        />
      </View>

      {/* Activity description */}
      <SectionTitle
        title="Activity Details"
        subtitle="Purpose and summary of the field visit"
      />

      <Info label="Activity" value={report.activity} />

      {/* Issues identified during the visit */}
      <SectionTitle
        title="Issues Identified"
        subtitle="Needs and concerns documented during the visit"
      />

      <Info
        label="General Issues"
        value={report.issues_identified}
      />

      <Info
        label="Education-Related Issues"
        value={report.education_related_issues}
      />

      <Info
        label="Health and Wellbeing Concerns"
        value={report.health_and_wellbeing_concerns}
      />

      <Info
        label="Family and Child Welfare"
        value={report.family_and_child_welfare_concerns}
      />

      <Info
        label="Livelihood and Financial Issues"
        value={report.livelihood_and_financial_issues}
      />

      <Info
        label="Government Schemes and Benefits"
        value={report.government_scheme_and_benefit_issues}
      />

      <Info
        label="Elderly and Disability Support Needs"
        value={report.elderly_and_disability_support_needs}
      />

      {/* Actions and support */}
      <SectionTitle
        title="Support and Actions"
        subtitle="Assistance provided and steps taken"
      />

      <Info
        label="Assistance Provided"
        value={report.assistance_provided}
      />

      <Info
        label="Actions Taken"
        value={report.actions_taken}
      />

      <Info
        label="Services or Benefits Accessed"
        value={report.services_or_benefits_accessed}
      />

      {/* Referrals and follow-up */}
      <SectionTitle
        title="Referrals and Follow-up"
        subtitle="Further support and planned next steps"
      />

      <Info
        label="Referrals Made"
        value={report.referrals_made}
      />

      <Info
        label="Referral Required"
        value={report.referral_required}
      />

      <Info
        label="Follow-up Required"
        value={report.follow_up_required}
      />

      <Info
        label="Follow-up Date"
        value={report.follow_up_date}
      />

      <Info
        label="Responsible Person"
        value={report.responsible_person}
      />

      {/* Outcomes and notes */}
      <SectionTitle
        title="Outcomes and Notes"
        subtitle="Progress and additional observations"
      />

      <Info
        label="Outcomes and Progress"
        value={report.outcomes_and_progress}
      />

      <Info
        label="Additional Notes"
        value={report.additional_notes}
      />

      {/* Source transcription */}
      <SectionTitle
        title="Voice Record"
        subtitle="Text associated with the recorded visit"
      />

      <Info
        label="Transcription / Translated Text"
        value={report.translated_text}
      />

      <View style={styles.footer}>
        <Text style={styles.footerTitle}>
          FIELD DOCUMENTATION
        </Text>

        <Text style={styles.footerText}>
          Please verify the details before submitting or sharing
          this report.
        </Text>
      </View>
    </View>
  );
}

// Reusable heading for each report section.
function SectionTitle({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <View style={styles.sectionHeader}>
      <View style={styles.sectionAccent} />

      <View style={styles.sectionText}>
        <Text style={styles.sectionTitle}>
          {title}
        </Text>

        <Text style={styles.sectionSubtitle}>
          {subtitle}
        </Text>
      </View>
    </View>
  );
}

// Reusable statistic card.
function StatCard({
  label,
  value,
}: {
  label: string;
  value: number | null | undefined;
}) {
  // Do not display invented or missing counts as zero.
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(value)
  ) {
    return null;
  }

  return (
    <View style={styles.statCard}>
      <Text style={styles.statValue}>
        {value}
      </Text>

      <Text style={styles.statLabel}>
        {label}
      </Text>
    </View>
  );
}

// Reusable field row. Empty and missing values are hidden.
function Info({
  label,
  value,
}: {
  label: string;
  value: string | number | undefined | null;
}) {
  const displayValue =
    typeof value === "string" ? value.trim() : value;

  if (
    displayValue === null ||
    displayValue === undefined ||
    displayValue === "" ||
    (
      typeof displayValue === "string" &&
      displayValue.toLowerCase() === "not mentioned"
    )
  ) {
    return null;
  }

  return (
    <View style={styles.info}>
      <Text style={styles.label}>
        {label}
      </Text>

      <Text style={styles.value}>
        {String(displayValue)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  // Main report container
  container: {
    backgroundColor: Colors.white,
    borderRadius: 20,
    padding: 18,
    borderWidth: 1,
    borderColor: Colors.border,
  },

  // Main report header
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingBottom: 20,
    marginBottom: 4,
    borderBottomWidth: 1,
    borderBottomColor: "#E8EDF2",
  },

  icon: {
    width: 48,
    height: 48,
    borderRadius: 15,
    backgroundColor: Colors.primaryLight,
    alignItems: "center",
    justifyContent: "center",
  },

  iconText: {
    color: Colors.success,
    fontSize: 23,
    fontWeight: "900",
  },

  headerText: {
    marginLeft: 13,
    flex: 1,
  },

  eyebrow: {
    color: Colors.primary,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1.3,
    marginBottom: 5,
  },

  title: {
    fontSize: 20,
    fontWeight: "800",
    color: Colors.text,
  },

  subtitle: {
    marginTop: 5,
    color: Colors.textSecondary,
    fontSize: 12,
    lineHeight: 18,
  },

  // Section headings
  sectionHeader: {
    flexDirection: "row",
    alignItems: "stretch",
    marginTop: 25,
    marginBottom: 7,
  },

  sectionAccent: {
    width: 4,
    borderRadius: 3,
    backgroundColor: Colors.primary,
    marginRight: 11,
  },

  sectionText: {
    flex: 1,
    paddingVertical: 2,
  },

  sectionTitle: {
    color: Colors.primary,
    fontSize: 16,
    fontWeight: "800",
  },

  sectionSubtitle: {
    color: Colors.textSecondary,
    fontSize: 11,
    lineHeight: 16,
    marginTop: 4,
  },

  // Information rows
  info: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#EEF1F5",
  },

  label: {
    fontSize: 11,
    fontWeight: "600",
    color: Colors.textSecondary,
    marginBottom: 5,
    letterSpacing: 0.2,
  },

  value: {
    fontSize: 14,
    color: Colors.text,
    fontWeight: "500",
    lineHeight: 22,
  },

  // Summary statistics
  statsContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginHorizontal: -4,
    marginTop: 5,
  },

  statCard: {
    flexGrow: 1,
    flexBasis: "28%",
    minWidth: 78,
    backgroundColor: "#F3F6FA",
    borderRadius: 13,
    borderWidth: 1,
    borderColor: "#E7ECF2",
    paddingHorizontal: 8,
    paddingVertical: 14,
    marginHorizontal: 4,
    marginVertical: 4,
    alignItems: "center",
    justifyContent: "center",
  },

  statValue: {
    color: Colors.primary,
    fontSize: 22,
    fontWeight: "900",
    textAlign: "center",
  },

  statLabel: {
    color: Colors.textSecondary,
    fontSize: 10,
    fontWeight: "600",
    textAlign: "center",
    lineHeight: 15,
    marginTop: 5,
  },

  // Report footer
  footer: {
    marginTop: 25,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: "#E8EDF2",
    alignItems: "center",
  },

  footerTitle: {
    color: Colors.textSecondary,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1.5,
  },

  footerText: {
    color: Colors.textSecondary,
    fontSize: 11,
    lineHeight: 17,
    textAlign: "center",
    marginTop: 7,
  },
});
