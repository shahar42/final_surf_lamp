# Render MCP Server Tools

Complete reference for all Render service management tools.

---

## render_deployments
Lists recent service deployment history with timestamps and status.

## render_service_status
Gets current status and health information for specific service.

## render_service_events
Analyzes recent service event logs with actionable insights.

## render_environment_vars
Shows configured environment variables with values partially masked.

## render_list_all_services
Lists all services in account with basic information.

## render_deploy_details
Shows details of specific deployment including commit information.

## render_services_status
Analyzes status of all services with cost overview.

## render_services_cost_analysis
Analyzes and suggests cost optimizations for all services.

## render_services_ssh_info
Gets SSH connection details for all services.

## render_restart_service
Restarts a specific running service immediately.

## render_suspend_service
Suspends a running service to stop billing.

## render_resume_service
Resumes a previously suspended service.

## render_scale_service
Scales service to specified number of instances.

## render_get_custom_domains
Lists custom domains configured for specific service.

## render_get_secret_files
Lists secret files configured for specific service.

## render_get_service_instances
Lists all running instances for specific service.

## render_list_env_groups
Lists all shared environment groups in account.

## render_list_disks
Lists all persistent disks in account.

## render_list_projects
Lists all projects in account for organization.

## render_get_user_info
Gets current Render user account information.

## render_list_maintenance_windows
Lists scheduled Render platform maintenance windows.

## render_delete_service
Permanently deletes a service. Caution: irreversible action.

## render_logs
Gets recent runtime service logs with filtering.

## search_render_logs
Searches for specific text patterns in logs.

## render_recent_errors
Gets recent errors and warnings from logs.

## render_latest_deployment_logs
Gets logs from most recent deployment for debugging.

## create_background_worker
Creates a new background worker service on Render.

## create_web_service
Creates a new web service on Render.

## trigger_deploy
Triggers a manual service deployment with optional cache clear.