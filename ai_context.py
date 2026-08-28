from datetime import datetime


def build_ai_context(
    weekly_data,
    performance_data,
    summary_data
):

    context = {

        "athlete": {

            "total_runs":
                performance_data.get(
                    "total_runs"
                ),

            "total_km":
                performance_data.get(
                    "total_km"
                ),

            "average_distance_km":
                performance_data.get(
                    "average_distance_km"
                ),

            "average_pace":
                performance_data.get(
                    "average_pace"
                )

        },


        "personal_bests": {

            "5k":
                performance_data.get(
                    "best_5k"
                ),

            "10k":
                performance_data.get(
                    "best_10k"
                ),

            "half_marathon":
                performance_data.get(
                    "best_half_marathon"
                ),

            "marathon":
                performance_data.get(
                    "best_marathon"
                )

        },


        "recent_training": {

            "weeks":
                weekly_data[-12:]

        },


        "summary": {

            "total_running_km":
                summary_data.get(
                    "total_running_km"
                ),

            "running_activities":
                summary_data.get(
                    "running_activities"
                ),

            "longest_run_km":
                summary_data.get(
                    "longest_run_km"
                )

        },


        "generated_at":
            datetime.now().isoformat()

    }


    return context