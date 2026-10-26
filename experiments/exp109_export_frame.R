# Exp 109: run giannella/snap_qc's munging script (eedb3f5) in a scratch copy and export its frame for Python.
# Two changes only, both pre-registered in exp109_rebuilt_inputs.md:
#   cpi_inflate_vars <- FALSE   (rebuilt amounts stay nominal, like our features; rows are unchanged)
#   the final frame is also written to exp109_frame.parquet
# Usage (from the scratch copy's root, with R_LIBS_USER pointing at the package library):
#   Rscript /path/to/experiments/exp109_export_frame.R
src <- "1_data_munging_and_raw_variable_reconstruction_for_using_public_qc_data.R"
code <- readLines(src)
flag <- grep("^cpi_inflate_vars <- TRUE$", code)
stopifnot(length(flag) == 1)
code[flag] <- "cpi_inflate_vars <- FALSE"
writeLines(code, "exp109_munging.R")
source("exp109_munging.R", echo = FALSE)
keep <- reg_model_data
for (nm in names(keep)) if (is.factor(keep[[nm]])) keep[[nm]] <- as.character(keep[[nm]])
arrow::write_parquet(keep, "exp109_frame.parquet")
cat("wrote exp109_frame.parquet:", nrow(keep), "rows,", ncol(keep), "columns\n")
