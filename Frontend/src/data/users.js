// User session profiles for demo and active role contexts.
// Connected to Supabase backend seeded users.

export const CURRENT_USER = {
  id: "usr-001",
  uuid: "4b987739-6880-4e65-a3c7-031bf7a59139",
  name: "Vickey Kumar",
  email: "vickey.kumar@company.com",
  department: "Engineering",
  role: "Software Engineer",
  manager: "Rahul Sharma",
  managerId: "usr-mgr-001",
  managerUuid: "28ac25ae-735f-4085-a6ed-c765be651ef1",
};

export const CURRENT_MANAGER = {
  id: "usr-mgr-001",
  uuid: "28ac25ae-735f-4085-a6ed-c765be651ef1",
  name: "Rahul Sharma",
  email: "rahul.sharma@company.com",
  department: "Engineering",
  role: "Engineering Manager",
};

export const CURRENT_FINANCE = {
  id: "usr-fin-001",
  uuid: "1dcd270f-f17b-40f9-a325-48979e93cd96",
  name: "Anita Joshi",
  email: "anita.joshi@company.com",
  department: "Finance",
  role: "Financial Controller",
};
