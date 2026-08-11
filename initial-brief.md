So we have a brief on a full stack web app to build. The project brief is in project-brief.md.

I want to plan out the full design before charging ahead with anything.

The tech stack will be Django (following the Hacksoft style guide conventions: <https://github.com/HackSoftware/Django-Styleguide>), and React w/ Vite, shadcn as the base for components. Deployment with Docker, postgres database. For the frontend we also want to ensure we are using zod for data schemas parsing and validation, react query for caching, and bulletproof reacts feature driven directory structure.

This repo will form the foundations for the development of the application going forward, hence the foundations need to be strong, well thought out, and scalable. This is why adherence to these standards of Hacksofts style guide & Bulletproof reacts feature driven directory structure for the frontend are incredibly important.

A big feature of the app is also the handling of it's multi tenancy. We will go with a single database multi tenancy design rather than single database, schema per tenant design. In order for this to work effectively, we need to introduce strong guardrails at all levels. Every request should have an associated tenant, set by the middlewares. All of our base models that are tenant scoped should have a base manager queryset that automatically sets the tenant of the ORM query to the tenant in flight (this will require having a tenant context variable that is set during the lifecycle of a request and then released).

All of our apis should use django rest framework API Views, with serializers defined inline for localisation of code (making it easier to read), each api should call one services layer function, and then return the response (with pagination). We need to implement a generic error handler that catches and parses all of the errors we could throw in the applicaiton. The hacksoft style guide has a good example of the sort of error handler that we should implement.

Roles based access controls should be handled in both the frontend and the backend, that is, pages or actions in the frontend should be gated by whether the user has the associated permission, and these should be enforced strongly in the backend, raising PermissionDenied errors whenever the user does not have the correct permission for the associated api.

So some concrete foundations:

### Backend

The data models need to be robust, favour hard database constrains on the models where possible so that we can enforce data integrity at the model level.

Always delegate api functions to a services layer function, having a strong standard from the beginning of the project is what allows the code to be scalable and maintainable for a team of developers.

Tenant integrity/isolation is incredibly important. It needs to be structured to minimise the chances of cross tenant data leaks, and cross tenant coupling on records in the db!! Hence why it needs to be centralised through one base tenant model that is shared across all tenant models.

### Frontend

Design ethos: I tend to gravitate towards interfaces that express a form of utilitarian minimalism. Every button, piece of information, heading, table header, etc, is chosen so that it actually delivers useful information to the end user, and it is presented in a way that aligns with the probablity of the user wanting to have access to that information at first glance. If there is a low probablity that the user will need to see something, it's often cleaner from an aesthetics perspective to hide it behind an icon with a popover, etc.

We also want the default interaction pattern to be -> creating something large (big form), then it deserves a dialog/modal. Creating something small -> can it be done inline? in a way that transforms the read only view of the data into an editable form. This is often a clean pattern, but each of these design decisions we can address on a case by case basis.

### Some initial data modelling decisions/ideas

Under the hood obviously we have the Tenant model, these are the organisations. Everything scoped to a tenant thus needs to inherit the tenant model.

A design decision is that one user is associated with one tenant for now, it's not within scope to open up to users that can span multiple tenants, so keep a simple tenant foreign key on the base user model.

There are three roles in the system: Directors, Mission Leads & Crew Members. These roles should be defined as base enums, and should be defined in the backend to inherit sets of permissions. That way, if the scope of the role changed at some point in the future, the only thing required to update the set of actions the user with the roles could perform would be a change to the underlying permission sets that the roles inherited.. likewise adding a new role would jsut be extending the enum class and defining its permission sets..

Example permissions could be: settings - view create, update, delete. Missions - create, view, update, approve, submit, approve_own, Skills - create, view, update, Assignments - create, accept, reject etc. QUESTION: what is the minimum set of permissions that can still effectively express all permutations of actions we want the users to be able to perform. Also want permissions for viewing different pages.

Skills are obviously something that are unique per tenant, so they should be configurable items. Could make sense to just have one generic skills table, with name, description. Crew members then select their skills and their profiency level on a scale of 1-10, some sort of through table of User, skill, profiency level.

Missions define the set of skills they want the crew members to have, alongside minimum profiency levels for each skill. Perhaps the mission might want one crew member proficient in one skill, and another proficient in another skill, the crew members shouldn't need to be sufficient in all of the skills required for the mission, the cumulative skill level of all of the crew members assigned to the mission should cover the set of all skills and proficiency levels that are required for the mission. Missions should also have a max number of crew members. The goal of the matching algorithm is to find all crew members who are available for the missions date range, and the combination of crew members that meet the minimum requirements of the mission. A Mission might also have a minimum number of crew members.

A crew member assigned to an active mission on x date is unavailable on day x. For now, we will keep it simple by not allowing crew members to define their availability, it is assumed they are available if they are not on an active mission. (This brings up the case where you are actively assigning to missions, if you assign a crew member to multiple missions on the same date before the missions are toggled active, then you need to ensure that your mission lifecycle double checks that the crew members that have been assigned to the mission have not been made unavailable because of another mission going active.)

Should a crew member be unavailable for assignment if they are assigned to an inactive mission that conflicts with the mission you are assigning for? Should it depend on the state of the mission that they have been assigned to? EG draft, awaiting approval

The lifecycle of missions should be controlled through a FSM (finite state machine). This makes the logic for how a missions transitions through its stages centralised, and easier to understand, minimising the chance of future extensions breaking the models flow. Also reduces the amount of code that will need to be changed going forward if a change was needed for the lifecycle of missions..

Assignments can be created by those who have the permissions (directors or mission leads), QUESTION: do crew members get to accept or reject assignments? Or should it be up to the mission lead? Simpler case is that mission leads can just assign crew members if they are available.. crew members can only be assigned to a mission if they satisy the minimum skill proficiency level for at least one skill requirement of the mission.
