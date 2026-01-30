"""HFS CLI entry point.

Command-line interface for the Hexagonal Frontend System.

Usage:
    hfs run --config config.yaml --request "Create a dashboard" --output-dir ./output
    hfs validate-config config.yaml
    hfs list-presets
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog='hfs',
        description='HFS - Hexagonal Frontend System CLI',
        epilog='For more information, see the documentation.'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        title='commands',
        dest='command',
        help='Available commands'
    )

    # ============================================================
    # run command
    # ============================================================
    run_parser = subparsers.add_parser(
        'run',
        help='Run the HFS pipeline',
        description='Run the HFS pipeline to generate frontend code'
    )

    run_parser.add_argument(
        '-c', '--config',
        type=str,
        required=True,
        help='Path to the configuration YAML file'
    )

    run_parser.add_argument(
        '-r', '--request',
        type=str,
        required=True,
        help='User request describing what to build'
    )

    run_parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='./output',
        help='Directory to save generated artifacts (default: ./output)'
    )

    run_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate inputs without running the full pipeline'
    )

    run_parser.add_argument(
        '--json',
        action='store_true',
        dest='output_json',
        help='Output results as JSON instead of formatted text'
    )

    # ============================================================
    # validate-config command
    # ============================================================
    validate_parser = subparsers.add_parser(
        'validate-config',
        help='Validate a configuration file',
        description='Validate an HFS configuration file for errors'
    )

    validate_parser.add_argument(
        'config_file',
        type=str,
        help='Path to the configuration YAML file to validate'
    )

    validate_parser.add_argument(
        '--json',
        action='store_true',
        dest='output_json',
        help='Output validation results as JSON'
    )

    # ============================================================
    # list-presets command
    # ============================================================
    presets_parser = subparsers.add_parser(
        'list-presets',
        help='List available triad presets',
        description='List all available triad presets with their descriptions'
    )

    presets_parser.add_argument(
        '--json',
        action='store_true',
        dest='output_json',
        help='Output presets as JSON'
    )

    presets_parser.add_argument(
        '--preset',
        type=str,
        choices=['hierarchical', 'dialectic', 'consensus'],
        help='Show detailed info for a specific preset'
    )

    return parser


def cmd_run(args: argparse.Namespace) -> int:
    """Execute the run command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    from ..core.config import load_config, ConfigError
    from ..core.orchestrator import HFSOrchestrator, HFSResult

    config_path = Path(args.config)
    output_dir = Path(args.output_dir)
    request = args.request

    # Validate config file exists
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        return 1

    # Load and validate configuration
    try:
        config = load_config(config_path)
        print(f"Configuration loaded successfully from: {config_path}")
        print(f"  Triads: {len(config.triads)}")
        print(f"  Sections: {len(config.sections)}")
        print(f"  Output format: {config.output.format}")
    except ConfigError as e:
        print(f"Error: Configuration validation failed: {e}", file=sys.stderr)
        return 1

    # Dry run - just validate inputs
    if args.dry_run:
        print("\n[Dry run] Configuration is valid. Pipeline would run with:")
        print(f"  Request: {request}")
        print(f"  Output directory: {output_dir}")
        return 0

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create orchestrator and run pipeline
    # Note: llm_client will be handled in Plan 02 with proper API key checks
    try:
        orchestrator = HFSOrchestrator(
            config_path=config_path,
            llm_client=None
        )

        print(f"\nRunning HFS pipeline...")
        print(f"  Request: {request}")
        print("-" * 60)

        # Run the async pipeline
        result = asyncio.run(orchestrator.run(request))

        # Handle results
        if result.success:
            _handle_success(result, output_dir, args.output_json)
            return 0
        else:
            _handle_failure(result, args.output_json)
            return 1

    except Exception as e:
        print(f"Error: Pipeline execution failed: {e}", file=sys.stderr)
        logger.exception("Pipeline execution failed")
        return 1


def _handle_success(result: Any, output_dir: Path, output_json: bool) -> None:
    """Handle successful pipeline execution.

    Args:
        result: HFSResult from the pipeline.
        output_dir: Directory to save artifacts.
        output_json: Whether to output JSON format.
    """
    if output_json:
        print(json.dumps(result.to_dict(), indent=2))
        return

    print("-" * 60)
    print("Pipeline completed successfully!")
    print()

    # Print phase timings
    print("Phase Timings:")
    for phase, timing in result.phase_timings.items():
        print(f"  {phase}: {timing:.2f}ms")

    total_time = sum(result.phase_timings.values())
    print(f"  Total: {total_time:.2f}ms")
    print()

    # Save artifacts
    if result.artifact and result.artifact.files:
        print(f"Artifacts ({result.artifact.file_count} files):")
        for file_path, content in result.artifact.files.items():
            full_path = output_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')
            print(f"  - {file_path} ({len(content)} chars)")
        print(f"\nArtifacts saved to: {output_dir}")
    else:
        print("No artifacts generated.")
    print()

    # Print validation status
    if result.validation:
        status = "PASSED" if result.validation.passed else "FAILED"
        print(f"Validation: {status}")
        if result.validation.issues:
            print(f"  Issues ({result.validation.summary.get('total', 0)} total):")
            for issue in result.validation.issues[:5]:  # Limit to first 5
                print(f"    [{issue.severity.value}] {issue.message}")
            if len(result.validation.issues) > 5:
                print(f"    ... and {len(result.validation.issues) - 5} more")
    print()

    # Print emergent report
    if result.emergent:
        print("Emergent Center Report:")
        print(f"  Overall Health: {result.emergent.overall_health}")
        print(f"  Coherence Score: {result.emergent.metrics.coherence_score:.2f}")
        print(f"  Style Consistency: {result.emergent.metrics.style_consistency:.2f}")
        print(f"  Interaction Consistency: {result.emergent.metrics.interaction_consistency:.2f}")

        if result.emergent.patterns.implicit_style:
            print(f"  Implicit Styles: {', '.join(result.emergent.patterns.implicit_style)}")

        if result.emergent.issues.coverage_gaps:
            print(f"  Coverage Gaps: {', '.join(result.emergent.issues.coverage_gaps)}")

        if result.emergent.recommendations:
            print("  Recommendations:")
            for rec in result.emergent.recommendations[:3]:  # Limit to top 3
                print(f"    - {rec}")

    # Save full report
    report_path = output_dir / "hfs_report.json"
    report_path.write_text(json.dumps(result.to_dict(), indent=2), encoding='utf-8')
    print(f"\nFull report saved to: {report_path}")


def _handle_failure(result: Any, output_json: bool) -> None:
    """Handle failed pipeline execution.

    Args:
        result: HFSResult from the pipeline.
        output_json: Whether to output JSON format.
    """
    if output_json:
        print(json.dumps({
            "success": False,
            "error": result.error,
            "phase_timings": result.phase_timings
        }, indent=2))
        return

    print("-" * 60)
    print("Pipeline failed!")
    print(f"Error: {result.error}")

    if result.phase_timings:
        print("\nPhases completed before failure:")
        for phase, timing in result.phase_timings.items():
            print(f"  {phase}: {timing:.2f}ms")


def cmd_validate_config(args: argparse.Namespace) -> int:
    """Execute the validate-config command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for valid, non-zero for invalid).
    """
    from ..core.config import load_config, ConfigError

    config_path = Path(args.config_file)

    # Check file exists
    if not config_path.exists():
        result = {
            "valid": False,
            "error": f"Configuration file not found: {config_path}",
            "path": str(config_path)
        }
        if args.output_json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    # Try to load and validate
    try:
        config = load_config(config_path)

        result = {
            "valid": True,
            "path": str(config_path),
            "summary": {
                "triads": len(config.triads),
                "triad_ids": [t.id for t in config.triads],
                "triad_presets": [t.preset for t in config.triads],
                "sections": config.sections,
                "output_format": config.output.format,
                "style_system": config.output.style_system,
                "pressure": {
                    "initial_temperature": config.pressure.initial_temperature,
                    "temperature_decay": config.pressure.temperature_decay,
                    "max_negotiation_rounds": config.pressure.max_negotiation_rounds
                }
            }
        }

        if args.output_json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Configuration is valid: {config_path}")
            print()
            print("Summary:")
            print(f"  Triads ({len(config.triads)}):")
            for triad in config.triads:
                print(f"    - {triad.id} ({triad.preset})")
                print(f"      Primary scope: {triad.scope.primary}")
                print(f"      Reach scope: {triad.scope.reach}")
            print()
            print(f"  Sections: {', '.join(config.sections)}")
            print(f"  Output format: {config.output.format}")
            print(f"  Style system: {config.output.style_system}")
            print()
            print("  Pressure settings:")
            print(f"    Initial temperature: {config.pressure.initial_temperature}")
            print(f"    Temperature decay: {config.pressure.temperature_decay}")
            print(f"    Max negotiation rounds: {config.pressure.max_negotiation_rounds}")
            print(f"    Escalation threshold: {config.pressure.escalation_threshold}")

        return 0

    except ConfigError as e:
        result = {
            "valid": False,
            "error": str(e),
            "path": str(config_path)
        }
        if args.output_json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Configuration validation failed: {config_path}", file=sys.stderr)
            print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_list_presets(args: argparse.Namespace) -> int:
    """Execute the list-presets command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (always 0).
    """
    from ..presets.triad_factory import list_available_presets, get_preset_info
    from ..core.triad import TriadPreset

    # If specific preset requested
    if args.preset:
        try:
            preset = TriadPreset(args.preset)
            info = get_preset_info(preset)

            if args.output_json:
                # Convert class to string for JSON serialization
                json_info = {
                    "name": args.preset,
                    "agent_roles": info["agent_roles"],
                    "best_for": info["best_for"],
                    "flow": info["flow"]
                }
                print(json.dumps(json_info, indent=2))
            else:
                print(f"Preset: {args.preset}")
                print("-" * 40)
                print(f"Agent Roles: {', '.join(info['agent_roles'])}")
                print(f"Flow: {info['flow']}")
                print()
                print("Best for:")
                for use_case in info['best_for']:
                    print(f"  - {use_case}")

            return 0
        except ValueError:
            print(f"Error: Unknown preset '{args.preset}'", file=sys.stderr)
            return 1

    # List all presets
    presets = list_available_presets()

    if args.output_json:
        # Convert for JSON serialization
        json_presets = {}
        for name, info in presets.items():
            json_presets[name] = {
                "agent_roles": info["agent_roles"],
                "best_for": info["best_for"],
                "flow": info["flow"]
            }
        print(json.dumps(json_presets, indent=2))
    else:
        print("Available Triad Presets")
        print("=" * 60)

        for name, info in presets.items():
            print()
            print(f"  {name}")
            print(f"  {'-' * len(name)}")
            print(f"  Agents: {', '.join(info['agent_roles'])}")
            print(f"  Flow: {info['flow']}")
            print(f"  Best for: {', '.join(info['best_for'])}")

        print()
        print("Use 'hfs list-presets --preset <name>' for more details.")

    return 0


def main() -> int:
    """Main entry point for the HFS CLI.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = create_argument_parser()
    args = parser.parse_args()

    # Configure logging based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('hfs').setLevel(logging.DEBUG)

    # Handle no command
    if args.command is None:
        print("HFS - Hexagonal Frontend System")
        print()
        print("A multi-agent system for generating frontend code through")
        print("structured negotiation between specialized triads.")
        print()
        parser.print_help()
        return 0

    # Dispatch to command handler
    command_handlers = {
        'run': cmd_run,
        'validate-config': cmd_validate_config,
        'list-presets': cmd_list_presets,
    }

    handler = command_handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        print(f"Error: Unknown command '{args.command}'", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
