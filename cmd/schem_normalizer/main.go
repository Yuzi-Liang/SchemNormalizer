package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"
)

func fileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

func findPython() string {
	if value := os.Getenv("SCHEM_NORMALIZER_PYTHON"); value != "" {
		return value
	}

	candidates := []string{
		filepath.Join(".venv", "Scripts", "python.exe"),
		filepath.Join(".venv", "bin", "python"),
	}

	for _, candidate := range candidates {
		if fileExists(candidate) {
			return candidate
		}
	}

	return "python"
}

func runPython(args []string) error {
	python := findPython()
	argv := append([]string{"-m", "schem_normalizer"}, args...)

	cmd := exec.Command(python, argv...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	if err := cmd.Run(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			os.Exit(exitErr.ExitCode())
		}
		return err
	}
	return nil
}

func main() {
	if len(os.Args) > 1 && !containsHelp(os.Args[1:]) {
		if err := runPython(os.Args[1:]); err != nil {
			fmt.Fprintln(os.Stderr, "Failed to run python:", err)
			os.Exit(1)
		}
		return
	}

	rootCmd := &cobra.Command{
		Use:                "schem_normalizer",
		Short:              "Wrapper for the Python schem_normalizer CLI",
		Long:               "A small Go wrapper that forwards arguments to the Python schem_normalizer module.",
		DisableFlagParsing: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 || containsHelp(args) {
				return cmd.Help()
			}
			return runPython(args)
		},
	}

	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func containsHelp(args []string) bool {
	for _, arg := range args {
		if arg == "-h" || arg == "--help" || strings.EqualFold(arg, "help") {
			return true
		}
	}
	return false
}
