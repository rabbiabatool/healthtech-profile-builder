export const GENDERS = [
  ["FEMALE", "Female"],
  ["MALE", "Male"],
  ["NON_BINARY", "Non-binary"],
  ["PREFER_NOT_TO_SAY", "Prefer not to say"],
];
export const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((group) => [group, group]);
export const ACTIVITY_LEVELS = [
  ["SEDENTARY", "Sedentary"],
  ["LIGHT", "Lightly active"],
  ["MODERATE", "Moderately active"],
  ["ACTIVE", "Very active"],
];
export const DIET_PREFERENCES = [
  ["NO_PREFERENCE", "No preference"],
  ["VEGETARIAN", "Vegetarian"],
  ["VEGAN", "Vegan"],
  ["HALAL", "Halal"],
  ["LOW_SUGAR", "Low sugar"],
  ["OTHER", "Other"],
];
export const REMINDER_CHANNELS = [
  ["NONE", "No reminders"],
  ["EMAIL", "Email"],
  ["SMS", "Text message"],
  ["APP", "In-app"],
];
export const RELATIONSHIPS = [
  ["PARENT", "Parent"],
  ["SPOUSE", "Spouse or partner"],
  ["SIBLING", "Sibling"],
  ["CHILD", "Child"],
  ["FRIEND", "Friend"],
  ["OTHER", "Other"],
];
export const PROFILE_STATUSES = [
  ["ACTIVE", "Active"],
  ["INACTIVE", "Inactive"],
];
export const COMPLETION_STATUSES = [
  ["NOT_STARTED", "Not started"],
  ["IN_PROGRESS", "In progress"],
  ["COMPLETE", "Complete"],
];
export const ORDERINGS = [
  ["-created_at", "Newest first"],
  ["created_at", "Oldest first"],
  ["-completion_percent", "Most complete first"],
  ["completion_percent", "Least complete first"],
];
export const AUDIT_ACTIONS = [
  ["DEMOGRAPHICS_UPDATED", "Demographics updated"],
  ["DEMOGRAPHICS_RESET", "Demographics reset"],
  ["WELLNESS_UPDATED", "Wellness preferences updated"],
  ["WELLNESS_RESET", "Wellness preferences reset"],
  ["EMERGENCY_CONTACT_CREATED", "Emergency contact added"],
  ["EMERGENCY_CONTACT_UPDATED", "Emergency contact updated"],
  ["EMERGENCY_CONTACT_DELETED", "Emergency contact deleted"],
  ["ADMIN_LOGIN", "Admin signed in"],
  ["ADMIN_LOGIN_FAILED", "Admin sign-in failed"],
  ["ADMIN_LOGOUT", "Admin signed out"],
  ["ADMIN_PROFILE_VIEWED", "Profile viewed by admin"],
  ["ADMIN_SEARCH_PERFORMED", "Profile search performed"],
  ["ADMIN_PROFILE_DEACTIVATED", "Profile deactivated"],
  ["ADMIN_PROFILE_REACTIVATED", "Profile reactivated"],
];
export const AUDIT_OUTCOMES = [
  ["SUCCESS", "Success"],
  ["FAILED", "Failed"],
];
export const ACTOR_ROLES = [
  ["USER", "Member"],
  ["ADMIN", "Admin"],
  ["ANONYMOUS", "Not signed in"],
];

export function labelOf(options, value) {
  const match = options.find(([code]) => code === value);
  return match ? match[1] : value || "—";
}