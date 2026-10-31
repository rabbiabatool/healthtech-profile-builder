# Small-Screen and Keyboard Verification Checklist (Week 2)

> **Status Note**: In this headless backend development environment without a live browser harness, automated unit and integration tests verify all HTTP contracts, CSRF tokens, authorization headers, and data integrity. The manual visual and physical device checks listed below are documented as a standardized QA protocol with status **MANUAL VERIFICATION PENDING**.

---

## 1. Member Section Reset & Profile Lifecycle Flows

### A. Viewport & Small-Screen Responsiveness (320px, 375px, 414px, 768px)
- [ ] **Viewport 320px (iPhone SE / narrow Android)**:
  - [ ] Profile overview cards stack vertically without horizontal scrollbars (`overflow-x: hidden`).
  - [ ] "Delete Section" and "Edit" action buttons maintain a minimum tap target size of 44x44 CSS pixels.
  - [ ] Section reset confirmation modals or dialogs scale to fit inside 320px width with comfortable padding.
  - [ ] Emergency contact cards wrap phone numbers and email addresses without text truncation or clipping.
  - [ ] Completion progress badge and percentage remain visible and legible at top of screen.
- [ ] **Viewport 768px (Tablet)**:
  - [ ] Grid layouts adjust cleanly between 1-column and 2-column displays.
  - [ ] Primary emergency contact badge is distinctly styled and positioned.

### B. Keyboard Navigation & Assistive Technology (WCAG 2.1 AA)
- [ ] **Tab Order & Focus Visibility**:
  - [ ] Tab sequence moves logically from header -> profile status -> section edit controls -> emergency contacts.
  - [ ] Every interactive control (Edit, Delete, Reset, Save, Cancel) displays a high-contrast focus ring (`outline: 2px solid`).
  - [ ] No keyboard traps exist in section edit forms or confirmation modals.
- [ ] **Modal Dialog Accessibility**:
  - [ ] Triggering "Delete Profile" or "Reset Section" traps focus inside the confirmation dialog.
  - [ ] Pressing `Escape` closes the confirmation dialog and returns focus to the initiating button.
  - [ ] Pressing `Enter` or `Space` activates the focused confirmation button.
- [ ] **ARIA & Screen Reader Semantics**:
  - [ ] Completion badge announces status (e.g., `aria-label="Profile completion: 100 percent, Complete"`).
  - [ ] Section reset buttons have descriptive accessible names (e.g., `aria-label="Reset Demographics Section"` instead of generic "Delete").
  - [ ] Form error messages are linked to their respective inputs via `aria-describedby` and `aria-invalid="true"`.

---

## 2. Administrator Dashboard & Deactivation Flows

### A. Viewport & Small-Screen Responsiveness
- [ ] **Admin Profile List (Table & Card Views)**:
  - [ ] On screens under 768px, admin table transforms into responsive data cards or horizontal scroll container with fixed header indicators.
  - [ ] Search input and filter dropdowns (Status: Active/Inactive, Completion) wrap neatly without overlapping.
  - [ ] Status toggle buttons ("Deactivate Profile", "Reactivate Profile") remain easily clickable with thumb reach.
- [ ] **Admin Detail & Audit Feed**:
  - [ ] Audit timeline cards display timestamp, action badge, and changed fields clearly on narrow screens.
  - [ ] Pagination controls ("Previous", "Next", page numbers) remain accessible without causing layout shift.

### B. Keyboard Navigation & Assistive Technology
- [ ] **Search & Filter Controls**:
  - [ ] Search input is focusable via `Tab` with an accessible label (`aria-label="Search profiles by name or email"`).
  - [ ] Filter dropdowns open and navigate options with `ArrowUp` / `ArrowDown` and select with `Enter`.
- [ ] **Deactivation Action Safety**:
  - [ ] Deactivation action requires explicit confirmation to prevent accidental keypresses.
  - [ ] Confirmation dialog focus lands on "Cancel" by default to prevent accidental destructive confirmation.
  - [ ] Success / failure toasts announce dynamically via `aria-live="polite"` region.

---

## 3. Verification Log Summary

| Check Area | Method | Automated Status | Manual Verification Status |
| :--- | :--- | :--- | :--- |
| **API Endpoints & Status Codes** | Pytest (`test_profile_lifecycle.py`) | **PASS** (24/24) | Verified via API |
| **CSRF Enforcement on Writes** | Pytest (`test_csrf_evidence.py`) | **PASS** (4/4) | Verified via API |
| **Admin Deactivation Route Security** | Pytest (`test_privilege_matrix.py`) | **PASS** | Verified via API |
| **Mobile Layout (320px–414px)** | Responsive Browser / DevTools | NOT RUN (Headless) | **PENDING MANUAL QA** |
| **Keyboard Tab Order & Focus Traps** | Physical Keyboard Testing | NOT RUN (Headless) | **PENDING MANUAL QA** |
| **Screen Reader Announcement** | NVDA / VoiceOver | NOT RUN (Headless) | **PENDING MANUAL QA** |

