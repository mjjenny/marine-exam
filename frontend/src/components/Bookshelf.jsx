import BookCover from "./BookCover.jsx";

/**
 * Static library bookshelf for the home page.
 * No scroll-linked motion — books sit on shelves and only lift on hover/focus.
 */
export default function Bookshelf({ subjects, onOpen }) {
  if (!subjects?.length) return null;

  return (
    <section
      className="bookshelf mt-4 overflow-hidden rounded-xl border border-[color:var(--border)] shadow-[var(--shadow)]"
      aria-label="Subject library"
      data-testid="bookshelf"
    >
      <div className="bookshelf-inner px-3 pb-4 pt-5 sm:px-5 sm:pb-5 sm:pt-6">
        <ul
          className="bookshelf-grid m-0 grid list-none grid-cols-2 gap-x-3 gap-y-0 p-0 sm:gap-x-4 md:grid-cols-3 lg:grid-cols-5"
          role="list"
        >
          {subjects.map((s) => (
            <li key={s.slug} className="bookshelf-slot flex flex-col items-center px-1 pt-2">
              <BookCover subject={s} onClick={() => onOpen(s)} />
              <span className="bookshelf-plank" aria-hidden="true" />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
