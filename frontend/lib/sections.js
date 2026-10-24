import {
  ACTIVITY_LEVELS,
  BLOOD_GROUPS,
  CONTACT_PREFERENCES,
  DIET_PREFERENCES,
  GENDERS,
  REMINDER_CHANNELS,
} from "./options";

export const DEMOGRAPHICS_REQUIRED = [
  { name: "date_of_birth", label: "Date of birth", type: "date" },
  { name: "gender", label: "Gender", as: "select", options: GENDERS },
];

export const DEMOGRAPHICS_OPTIONAL = [
  { name: "blood_group", label: "Blood group", as: "select", options: BLOOD_GROUPS },
  { name: "height_cm", label: "Height (cm)", type: "number", inputMode: "decimal", step: "0.1", min: "30", max: "272" },
  { name: "weight_kg", label: "Weight (kg)", type: "number", inputMode: "decimal", step: "0.1", min: "2", max: "650" },
  { name: "country", label: "Country", maxLength: 60, autoComplete: "country-name" },
  { name: "preferred_language", label: "Preferred language", maxLength: 40 },
];

export const WELLNESS_REQUIRED = [
  { name: "contact_preference", label: "Contact preference", as: "select", options: CONTACT_PREFERENCES },
  { name: "wellness_goals", label: "Wellness goals", as: "textarea", rows: 3, maxLength: 500, wide: true, hint: "Fictional notes only." },
];

export const WELLNESS_OPTIONAL = [
  { name: "activity_level", label: "Activity level", as: "select", options: ACTIVITY_LEVELS },
  { name: "diet_preference", label: "Diet preference", as: "select", options: DIET_PREFERENCES },
  { name: "sleep_goal_hours", label: "Sleep goal (hours)", type: "number", inputMode: "decimal", step: "0.5", min: "3", max: "14" },
  { name: "reminder_channel", label: "Reminder channel", as: "select", options: REMINDER_CHANNELS },
  { name: "allergy_notes", label: "Allergy notes", as: "textarea", rows: 3, maxLength: 1000, wide: true, hint: "Fictional notes only." },
  { name: "condition_notes", label: "Condition notes", as: "textarea", rows: 3, maxLength: 1000, wide: true, hint: "Fictional notes only." },
];