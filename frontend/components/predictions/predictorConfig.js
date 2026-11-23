export const FIELD_ORDER = [
  "age",
  "lead_time_days",
  "scheduled_hour",
  "day_of_week",
  "appointment_type",
  "reminder_sent",
  "previous_appointments",
  "previous_no_shows",
  "distance_km",
];

export const LABELS = {
  age: "Age (years)",
  lead_time_days: "Lead time (days)",
  scheduled_hour: "Appointment hour (24-hour clock)",
  day_of_week: "Day of the week",
  appointment_type: "Appointment type",
  reminder_sent: "A reminder was sent",
  previous_appointments: "Previous appointments",
  previous_no_shows: "Previous no-shows",
  distance_km: "Distance to the clinic (km, optional)",
};

export const HINTS = {
  lead_time_days: "Days between booking and the appointment.",
  scheduled_hour: "For example, 14 means 2 pm.",
  previous_no_shows: "Cannot be more than previous appointments.",
  distance_km: "Leave empty if unknown.",
};

export const OPTION_LABELS = {
  MON: "Monday",
  TUE: "Tuesday",
  WED: "Wednesday",
  THU: "Thursday",
  FRI: "Friday",
  CHECKUP: "Check-up",
  FOLLOW_UP: "Follow-up",
  VACCINATION: "Vaccination",
  LAB_TEST: "Lab test",
  SPECIALIST: "Specialist",
};

export const PRESETS = [
  {
    name: "Routine check-up with a reminder",
    values: {
      age: "46", lead_time_days: "7", scheduled_hour: "10", day_of_week: "TUE",
      appointment_type: "CHECKUP", reminder_sent: true, previous_appointments: "12",
      previous_no_shows: "1", distance_km: "4.5",
    },
  },
  {
    name: "Long wait, no reminder, past no-shows",
    values: {
      age: "27", lead_time_days: "75", scheduled_hour: "16", day_of_week: "FRI",
      appointment_type: "SPECIALIST", reminder_sent: false, previous_appointments: "8",
      previous_no_shows: "4", distance_km: "22",
    },
  },
  {
    name: "Short-notice follow-up, distance unknown",
    values: {
      age: "63", lead_time_days: "3", scheduled_hour: "9", day_of_week: "WED",
      appointment_type: "FOLLOW_UP", reminder_sent: true, previous_appointments: "20",
      previous_no_shows: "0", distance_km: "",
    },
  },
];

export const BAND_TEXT = {
  LOW: {
    title: "Lower band",
    text: "Among the lowest-scoring third of appointments in the model's training data.",
  },
  MEDIUM: {
    title: "Middle band",
    text: "In the middle third of scores in the model's training data.",
  },
  HIGH: {
    title: "Higher band",
    text: "At or above the model's operating threshold: among the highest-scoring third.",
  },
};

export const DEFAULT_DISCLAIMER =
  "Educational prototype trained on synthetic data. Not clinically validated, not medical advice, and not for decisions about anyone's care.";

export const asPercent = (value) => `${Math.round(value * 100)}%`;

export function buildPayload(values, info) {
  const schema = info.input_schema;
  const nullable = new Set(schema.nullable);
  const payload = {};
  for (const name of FIELD_ORDER) {
    if (name in schema.numeric_ranges) {
      const raw = String(values[name] ?? "").trim();
      if (raw === "") {
        payload[name] = null;
      } else {
        const number = Number(raw);
        payload[name] = Number.isNaN(number) ? raw : number;
      }
    } else if (schema.boolean.includes(name)) {
      payload[name] = Boolean(values[name]);
    } else {
      payload[name] = values[name];
    }
  }
  return payload;
}

export function splitErrors(data, fields) {
  const fieldErrors = {};
  const general = [];
  if (!data || typeof data !== "object") {
    return { fieldErrors, general: ["The request was rejected."] };
  }
  for (const [key, value] of Object.entries(data)) {
    const message = Array.isArray(value) ? value.join(" ") : String(value);
    if (fields.includes(key)) {
      fieldErrors[key] = message;
    } else if (key === "detail" || key === "non_field_errors") {
      general.push(message);
    } else {
      general.push(`${key}: ${message}`);
    }
  }
  return { fieldErrors, general };
}