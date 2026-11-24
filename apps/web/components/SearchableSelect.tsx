"use client";

import { type KeyboardEvent as ReactKeyboardEvent, useEffect, useId, useMemo, useRef, useState } from "react";

export type SelectOption = {
  value: string;
  label: string;
};

export type SelectOptionGroup = {
  label: string;
  options: readonly SelectOption[];
};

type Props = {
  value: string;
  onChange: (value: string) => void;
  options?: readonly SelectOption[];
  groups?: readonly SelectOptionGroup[];
  placeholder?: string;
  searchPlaceholder?: string;
  ariaLabel?: string;
  disabled?: boolean;
  className?: string;
};

export function SearchableSelect({
  value,
  onChange,
  options = [],
  groups = [],
  placeholder = "Select an option",
  searchPlaceholder = "Search options...",
  ariaLabel,
  disabled = false,
  className = "",
}: Props) {
  const id = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  const allOptions = useMemo(
    () => [...options, ...groups.flatMap((group) => group.options)],
    [groups, options],
  );
  const selectedOption = allOptions.find((option) => option.value === value);
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const filteredOptions = useMemo(() => {
    const matches = (option: SelectOption) => (
      !normalizedQuery
      || option.label.toLocaleLowerCase().includes(normalizedQuery)
      || option.value.toLocaleLowerCase().includes(normalizedQuery)
    );
    if (groups.length) {
      return groups.flatMap((group) => group.options.filter(matches));
    }
    return options.filter(matches);
  }, [groups, normalizedQuery, options]);
  const filteredGroups = useMemo(
    () => groups.map((group) => ({ ...group, options: group.options.filter((option) => (
      !normalizedQuery
      || option.label.toLocaleLowerCase().includes(normalizedQuery)
      || option.value.toLocaleLowerCase().includes(normalizedQuery)
    )) })).filter((group) => group.options.length > 0),
    [groups, normalizedQuery],
  );

  useEffect(() => {
    if (open) searchRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function closeOnOutsidePointer(event: PointerEvent) {
      if (event.target instanceof Node && !rootRef.current?.contains(event.target)) setOpen(false);
    }
    function closeOnEscape(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  useEffect(() => {
    if (open) document.getElementById(`${id}-option-${activeIndex}`)?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, id, open]);

  function choose(option: SelectOption) {
    onChange(option.value);
    setOpen(false);
    setQuery("");
    triggerRef.current?.focus();
  }

  function handleSearchKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => Math.min(index + 1, filteredOptions.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === "Home" && filteredOptions.length) {
      event.preventDefault();
      setActiveIndex(0);
    } else if (event.key === "End" && filteredOptions.length) {
      event.preventDefault();
      setActiveIndex(filteredOptions.length - 1);
    } else if (event.key === "Enter" && filteredOptions[activeIndex]) {
      event.preventDefault();
      choose(filteredOptions[activeIndex]);
    }
  }

  let optionIndex = 0;
  const renderOption = (option: SelectOption) => {
    const currentIndex = optionIndex++;
    return (
      <button
        id={`${id}-option-${currentIndex}`}
        key={option.value}
        className={`searchable-select-option${value === option.value ? " selected" : ""}${activeIndex === currentIndex ? " active" : ""}`}
        type="button"
        role="option"
        aria-selected={value === option.value}
        onMouseEnter={() => setActiveIndex(currentIndex)}
        onClick={() => choose(option)}
      >
        <span>{option.label}</span>
        {value === option.value && <span className="searchable-select-check" aria-hidden="true">✓</span>}
      </button>
    );
  };

  return (
    <div className={`searchable-select ${className}`.trim()} ref={rootRef}>
      <button
        ref={triggerRef}
        className="searchable-select-trigger"
        type="button"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => {
          setQuery("");
          if (!open) setActiveIndex(Math.max(0, allOptions.findIndex((option) => option.value === value)));
          setOpen(!open);
        }}
      >
        <span className={selectedOption ? "" : "searchable-select-placeholder"}>
          {selectedOption?.label ?? (value || placeholder)}
        </span>
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 7.5 5 5 5-5" /></svg>
      </button>
      {open && (
        <div className="searchable-select-popover">
          <label className="searchable-select-search">
            <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" /><path d="m13 13 4 4" /></svg>
            <input
              ref={searchRef}
              type="search"
              role="combobox"
              aria-label={ariaLabel ? `Search ${ariaLabel.toLocaleLowerCase()}` : "Search options"}
              aria-expanded="true"
              aria-controls={`${id}-listbox`}
              aria-activedescendant={filteredOptions[activeIndex] ? `${id}-option-${activeIndex}` : undefined}
              autoComplete="off"
              placeholder={searchPlaceholder}
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setActiveIndex(0);
              }}
              onKeyDown={handleSearchKeyDown}
            />
          </label>
          <div className="searchable-select-options" id={`${id}-listbox`} role="listbox" aria-label={ariaLabel ?? "Options"}>
            {groups.length
              ? filteredGroups.map((group) => (
                <div className="searchable-select-group" role="group" aria-label={group.label} key={group.label}>
                  <span className="searchable-select-group-label">{group.label}</span>
                  {group.options.map(renderOption)}
                </div>
              ))
              : filteredOptions.map(renderOption)}
            {!filteredOptions.length && <div className="searchable-select-empty">No options found</div>}
          </div>
        </div>
      )}
    </div>
  );
}
