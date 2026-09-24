import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
export type LoginInput = z.infer<typeof loginSchema>;

export const memberSchema = z.object({
  roll_no: z.string().min(1, "Roll number is required"),
  name: z.string().min(1, "Name is required"),
  dept: z.string().optional(),
  year: z.string().optional(),
  consent: z.boolean().refine((v) => v === true, "Consent is required to enroll a member"),
});
export type MemberInput = z.infer<typeof memberSchema>;

export const eventSchema = z.object({
  name: z.string().min(1, "Event name is required"),
  date: z.string().min(1, "Date is required"),
});
export type EventInput = z.infer<typeof eventSchema>;
